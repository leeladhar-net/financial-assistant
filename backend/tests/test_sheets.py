import pytest
from app.integrations.google.sheets_service import GoogleSheetsService

def test_extract_sheet_id():
    url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
    sheet_id = GoogleSheetsService.extract_sheet_id(url)
    assert sheet_id == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

@pytest.mark.asyncio
async def test_analyze_sheet():
    url = "https://docs.google.com/spreadsheets/d/sample_sheet_id/edit"
    res = await GoogleSheetsService.analyze_sheet(url)
    
    assert res.title is not None
    assert res.row_count == 5
    assert len(res.declined_over_5pct) > 0
    symbols_down = [r["symbol"] for r in res.declined_over_5pct]
    assert "NVDA" in symbols_down or "TSLA" in symbols_down
