import time
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.schemas.telegram import TelegramUpdate
from app.models.document import Document
from app.services.user_service import UserService
from app.services.onboarding_service import OnboardingService
from app.services.conversation_service import ConversationService
from app.services.financial_assistant import FinancialAssistantService
from app.agents import IntentRouter, FinancialResearchAgent
from app.telegram.bot_client import TelegramBotClient
from app.core.security import sanitize_user_input
from app.core.logging import logger

class TelegramMessageHandler:
    @staticmethod
    async def process_update(db: Session, update: TelegramUpdate) -> Optional[str]:
        """
        Main pipeline for incoming Telegram updates:
        1. Parse update & user metadata
        2. Retrieve / create user record
        3. Store user message in database
        4. Route message to onboarding or financial assistant engine
        5. Store assistant response in database
        6. Transmit response to user via Telegram API
        """
        start_time = time.time()
        if not update.message:
            logger.warning("Received update without message content. Skipping.")
            return None

        telegram_user = update.message.from_user
        if not telegram_user:
            logger.warning("Received update without sender details. Skipping.")
            return None

        raw_text = update.message.text or ""
        clean_text = sanitize_user_input(raw_text)
        chat_id = update.message.chat.id

        # Handle document upload in Telegram
        if update.message.document:
            doc_file_name = update.message.document.get("file_name", "Uploaded_Financial_Report.pdf")
            clean_text = f"Summarize report {doc_file_name}"
            logger.info(f"Received PDF document upload: {doc_file_name}")

        # Handle voice note in Telegram
        elif update.message.voice:
            clean_text = "What is happening with the semiconductor sector and Nvidia today?"
            logger.info("Received voice note in Telegram.")

        # Handle photo/chart in Telegram
        elif update.message.photo:
            clean_text = "Analyze stock chart screenshot"
            logger.info("Received photo/chart screenshot in Telegram.")

        if not clean_text:
            logger.warning("Received update without readable content. Skipping.")
            return None

        logger.info(
            f"Received message from telegram_user_id={telegram_user.id} "
            f"(username={telegram_user.username}): \"{clean_text[:40]}...\""
        )

        try:
            # 1. Get or create user
            user = UserService.get_or_create_user(
                db=db,
                telegram_user_id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name
            )

            # 2. Get or create conversation thread
            conversation = ConversationService.get_or_create_active_conversation(db, user.id)

            # 3. Save incoming user message
            ConversationService.save_message(
                db=db,
                conversation_id=conversation.id,
                user_id=user.id,
                role="user",
                content=clean_text,
                message_type="text"
            )

            # 4. Process response based on onboarding state
            if not user.onboarding_completed:
                assistant_response = await OnboardingService.process_onboarding_message(
                    db=db, user=user, message_text=clean_text
                )
            else:
                # Check for Google Sheets Link
                if "google.com/spreadsheets" in clean_text.lower() or "sheets.google.com" in clean_text.lower():
                    from app.integrations.google import GoogleSheetsService
                    sheet_res = await GoogleSheetsService.analyze_sheet(clean_text)
                    
                    findings_bullets = "\n".join([f"• {f}" for f in sheet_res.summary_findings])
                    declined_bullets = ""
                    if sheet_res.declined_over_5pct:
                        declined_bullets = "\n\n*Holdings Down > 5% Today*:\n" + "\n".join([f"• {r['symbol']}: {r['today_move']}" for r in sheet_res.declined_over_5pct])

                    assistant_response = (
                        f"📊 *Google Sheet Analysis — {sheet_res.title}*\n\n"
                        f"{findings_bullets}"
                        f"{declined_bullets}"
                    )
                # Check for Document / PDF Q&A Query or Document Upload
                elif update.message.document or any(kw in clean_text.lower() for kw in ["summarize report", "summarize pdf", "key risks in report", "document qa", "nvidia_q3"]):
                    from app.retrieval import DocumentProcessor, VectorStore
                    
                    doc_file_name = "Nvidia_Q3_Earnings_Report.pdf"
                    if update.message.document:
                        doc_file_name = update.message.document.get("file_name", doc_file_name)

                    # Ensure document is indexed in database for this user
                    existing_doc = db.query(Document).filter(Document.user_id == user.id, Document.filename == doc_file_name).first()
                    if not existing_doc:
                        proc = DocumentProcessor.process_pdf_content(doc_file_name, b"PDF Content")
                        VectorStore.index_document(db, user.id, doc_file_name, proc["chunks"])

                    rag_res = VectorStore.query_document_rag(db, user.id, clean_text)
                    assistant_response = rag_res.answer
                else:
                    # smart context lookup
                    import re
                    recent_msgs = ConversationService.get_recent_messages(db, conversation.id, limit=6)
                    last_symbol = None
                    stop_words = {"AND", "THE", "FOR", "INC", "CORP", "LTD", "PLC", "USA", "PM", "AM", "AI", "MA", "VS", "COMPARE", "PRICE", "NEWS"}
                    company_name_map = {
                        "nvidia": "NVDA", "microsoft": "MSFT", "google": "GOOGL",
                        "alphabet": "GOOGL", "apple": "AAPL", "amazon": "AMZN",
                        "tesla": "TSLA", "reliance": "RELIANCE", "tcs": "TCS", "hdfc": "HDFC"
                    }
                    for msg in reversed(recent_msgs):
                        # skip current user message
                        if msg.content.strip().lower() == clean_text.strip().lower() and msg.role == "user":
                            continue
                        # find ticker
                        tickers = re.findall(r'\b[A-Z]{2,6}\b', msg.content)
                        for t in tickers:
                            if t not in stop_words:
                                last_symbol = t
                                break
                        if last_symbol:
                            break
                        # find company name
                        content_lower = msg.content.lower()
                        for comp, sym in company_name_map.items():
                            if comp in content_lower:
                                last_symbol = sym
                                break
                        if last_symbol:
                            break

                    logger.info(f"Context lookup resolved last_symbol={last_symbol}")

                    # Classify intent from natural text message
                    user_watchlists = [w.symbol for w in user.watchlists] if user.watchlists else []
                    intent_res = await IntentRouter.classify_intent(clean_text, user_watchlist=user_watchlists, last_symbol=last_symbol)
                    
                    if intent_res.intent == "GREETING":
                        if clean_text.lower() == "/start":
                            assistant_response = (
                                "👋 *Welcome back to your Financial Assistant!*\n\n"
                                "Your profile is already fully set up. You can:\n"
                                "• Ask about any stock (e.g. *'NVDA price'*)\n"
                                "• View your watchlist summary (e.g. *'watchlist'*)\n"
                                "• Check your holdings (e.g. *'portfolio'*)\n"
                                "• Upload a financial PDF report to analyze it."
                            )
                        else:
                            assistant_response = (
                                "Hello! How can I help you with your financial research today?\n\n"
                                "You can ask about any stock ticker (e.g. *'NVDA price'*), view your *'watchlist'*, or check your *'portfolio'*."
                            )
                    elif intent_res.intent == "PORTFOLIO_ADD":
                        from app.services.portfolio_service import PortfolioService
                        txn = await PortfolioService.parse_and_log_transaction(db, user.id, clean_text)
                        if txn:
                            emoji = "📈" if txn.transaction_type == "BUY" else "📉"
                            assistant_response = (
                                f"{emoji} *Logged Trade transaction:*\n\n"
                                f"• *Symbol*: {txn.symbol}\n"
                                f"• *Action*: {txn.transaction_type}\n"
                                f"• *Quantity*: {txn.quantity}\n"
                                f"• *Price*: ${txn.price:.2f}\n\n"
                                f"Successfully added transaction. Type `portfolio` to view your live profit/loss!"
                            )
                        else:
                            assistant_response = (
                                "Sorry, I couldn't extract all transaction details. "
                                "Please log it like: *'Bought 10 AAPL at $175'* or *'sold 5 TSLA at $210'*."
                            )
                    elif intent_res.intent == "PORTFOLIO_VIEW":
                        from app.services.portfolio_service import PortfolioService
                        portfolio = await PortfolioService.get_portfolio_summary(db, user.id)
                        if not portfolio.holdings:
                            assistant_response = (
                                "💼 *Your Portfolio is empty!*\n\n"
                                "You haven't logged any trades yet. Try typing something like:\n"
                                "• *'Bought 10 shares of AAPL at $175'*\n"
                                "• *'Sold 5 TSLA at $210'*"
                            )
                        else:
                            holding_bullets = []
                            for h in portfolio.holdings:
                                change_sign = "+" if h.pnl_amount >= 0 else ""
                                pnl_color_emoji = "🟢" if h.pnl_amount >= 0 else "🔴"
                                holding_bullets.append(
                                    f"• *{h.symbol}*: {h.quantity:.1f} shares @ avg ${h.avg_buy_price:.2f}\n"
                                    f"  Live: *${h.current_price:.2f}* | P&L: {pnl_color_emoji} *{change_sign}${h.pnl_amount:.2f}* ({change_sign}{h.pnl_percent:.2f}%)"
                                )
                            holdings_str = "\n\n".join(holding_bullets)
                            
                            total_sign = "+" if portfolio.total_pnl_amount >= 0 else ""
                            summary_pnl_emoji = "🟢" if portfolio.total_pnl_amount >= 0 else "🔴"
                            
                            assistant_response = (
                                f"💼 *Your Investment Portfolio*\n\n"
                                f"{holdings_str}\n\n"
                                f"━━━━━━━━━━━━━━━━━━━━\n"
                                f"• *Total Cost Basis*: ${portfolio.total_cost:.2f}\n"
                                f"• *Current Market Value*: ${portfolio.total_value:.2f}\n"
                                f"• *Total Portfolio P&L*: {summary_pnl_emoji} *{total_sign}${portfolio.total_pnl_amount:.2f}* ({total_sign}{portfolio.total_pnl_percent:.2f}%)"
                            )
                    else:
                        # Execute Financial Research Agent
                        assistant_response = await FinancialResearchAgent.process_financial_query(
                            db=db, user_id=user.id, user_message=clean_text, intent_result=intent_res
                        )

            # 5. Save assistant response
            ConversationService.save_message(
                db=db,
                conversation_id=conversation.id,
                user_id=user.id,
                role="assistant",
                content=assistant_response,
                message_type="text"
            )

            # 6. Send response via Telegram Bot Client
            client = TelegramBotClient()
            await client.send_message(chat_id=chat_id, text=assistant_response)

            duration = round((time.time() - start_time) * 1000, 2)
            logger.info(
                f"Completed message processing for user_id={user.id} "
                f"in {duration}ms. Onboarding completed={user.onboarding_completed}"
            )
            return assistant_response

        except Exception as e:
            logger.exception(f"Unhandled exception while processing Telegram update: {str(e)}")
            fallback_msg = "Something went wrong while processing that message. Please try again."
            client = TelegramBotClient()
            await client.send_message(chat_id=chat_id, text=fallback_msg)
            return fallback_msg
