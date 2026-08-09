import pytest
from app.services.mapping_engine import CompanyMappingEngine

@pytest.mark.asyncio
async def test_mapping_engine_layer1_exact():
    # Zomato exact alias
    i1 = await CompanyMappingEngine.resolve_instrument("zomato")
    assert i1 is not None
    assert i1.ticker == "ETERNAL.NS"
    assert i1.symbol == "ETERNAL"

    # NVIDIA exact alias
    i2 = await CompanyMappingEngine.resolve_instrument("nvidia")
    assert i2 is not None
    assert i2.ticker == "NVDA"
    assert i2.symbol == "NVDA"

@pytest.mark.asyncio
async def test_mapping_engine_layer2_normalized():
    # Tata Motors normalized
    i1 = await CompanyMappingEngine.resolve_instrument("Tata Motors Ltd")
    assert i1 is not None
    assert i1.ticker == "TMCV.NS"
    assert i1.symbol == "TMCV"

    # Wipro normalized
    i2 = await CompanyMappingEngine.resolve_instrument("Wipro Co")
    assert i2 is not None
    assert i2.ticker == "WIPRO.NS"
    assert i2.symbol == "WIPRO"

@pytest.mark.asyncio
async def test_mapping_engine_layer3_search():
    # Live Search validation
    i1 = await CompanyMappingEngine.resolve_instrument("Aditya Birla Sun Life Mutual")
    assert i1 is not None
    assert "BO" in i1.ticker or "NS" in i1.ticker
