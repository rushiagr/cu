import datetime
from collections import defaultdict
from decimal import Decimal

from pfnav import NavManager, Transaction, TransactionType, calculate_pf_nav, calculate_pf_nav2


def test_portfolio_nav_calculation():
    # Setup test data
    jan1 = datetime.date(2024, 1, 1)
    jan2 = datetime.date(2024, 1, 2)
    jan3 = datetime.date(2024, 1, 3)
    jan4 = datetime.date(2024, 1, 4)

    # Transactions
    txns = [
        Transaction(mf_name="MF1", date=jan1, txn_type=TransactionType.BUY, units=Decimal("100"), nav=Decimal("100")),
        Transaction(mf_name="MF2", date=jan2, txn_type=TransactionType.BUY, units=Decimal("100"), nav=Decimal("110")),
    ]

    # NAV history including all dates and funds
    nav_history = NavManager(
        navs={
            jan1: {"MF1": Decimal("100"), "MF2": Decimal("100")},  # Not used but available
            jan2: {"MF1": Decimal("110"), "MF2": Decimal("110")},
            jan3: {"MF1": Decimal("121"), "MF2": Decimal("132")},
            jan4: {"MF1": Decimal("110"), "MF2": Decimal("110")},
        },
        current_date=jan4,
    )

    # Calculate portfolio NAV
    result = calculate_pf_nav(txns, nav_history)
    result2 = calculate_pf_nav2(txns, nav_history)

    # Expected values based on your example:
    # Jan 1: Base NAV = 1000
    # Jan 2: 10% increase = 1100
    # Jan 3: 15% increase from 1100 = 1265
    # Jan 4: back to 1100

    expected = [
        (jan1, Decimal("1000.0")),
        (jan2, Decimal("1100.0")),
        (jan3, Decimal("1265.0")),
        (jan4, Decimal("1100.0")),
    ]

    assert len(result) == len(expected)
    for (date, nav), (exp_date, exp_nav) in zip(result, expected):
        assert date == exp_date
        assert nav == exp_nav, f"On {date}, expected NAV {exp_nav} but got {nav}"

    assert len(result2) == len(expected)
    for (date, nav), (exp_date, exp_nav) in zip(result2, expected):
        assert date == exp_date
        assert nav == exp_nav, f"On {date}, expected NAV {exp_nav} but got {nav}"


def test_portfolio_nav_calculation2():
    # Original test case plus sell scenario
    jan1 = datetime.date(2024, 1, 1)
    jan2 = datetime.date(2024, 1, 2)
    jan3 = datetime.date(2024, 1, 3)
    jan4 = datetime.date(2024, 1, 4)
    jan5 = datetime.date(2024, 1, 5)

    # Test scenario:
    # Jan 1: Buy MF1 100 units @ 100 (10,000)
    # Jan 2: Value rises 10% + Buy MF2 100 units @ 110 (11,000)
    # Jan 3: Both rise ~10% + Sell 50 units of MF1 @ 121
    # Jan 4: Both drop back to 110
    txns = [
        Transaction(mf_name="MF1", date=jan1, txn_type=TransactionType.BUY, units=Decimal("100"), nav=Decimal("100")),
        Transaction(mf_name="MF2", date=jan2, txn_type=TransactionType.BUY, units=Decimal("100"), nav=Decimal("110")),
        Transaction(mf_name="MF1", date=jan3, txn_type=TransactionType.SELL, units=Decimal("50"), nav=Decimal("121")),
    ]

    nav_history = NavManager(
        navs={
            jan1: {"MF1": Decimal("100"), "MF2": Decimal("100")},
            jan2: {"MF1": Decimal("110"), "MF2": Decimal("110")},
            jan3: {"MF1": Decimal("121"), "MF2": Decimal("121")},
            jan4: {"MF1": Decimal("110"), "MF2": Decimal("110")},
            jan5: {"MF1": Decimal("99"), "MF2": Decimal("88")},  # 10% drop and 20% drop respectively
        },
        current_date=jan5,
    )

    result = calculate_pf_nav(txns, nav_history)
    result2 = calculate_pf_nav2(txns, nav_history)

    # Let's calculate expected values:
    # Jan 1: Initial investment 10,000 -> NAV 1000
    # Jan 2:
    #   - MF1 rises 10% (11,000)
    #   - Buy MF2 for 11,000
    #   - NAV should reflect only MF1's rise = 1100
    # Jan 3:
    #   - Both rise 10% -> value = (50 MF1 + 100 MF2) * 121 = 18,150
    #   - NAV before sell = ~1210
    #   - Sell 50 MF1 @ 121 = 6,050 withdrawal
    #   - Final NAV should still be ~1210 (sell shouldn't affect performance)
    # Jan 4: Both drop to 110 -> NAV drops proportionally to ~1100

    expected = [
        (jan1, Decimal("1000.0")),
        (jan2, Decimal("1100.0")),
        (jan3, Decimal("1210.0")),
        (jan4, Decimal("1100.0")),
        # By Jan 5, We have 50 units of MF1 NAV 99 (10% drop from 110) & 100 units of MF2 NAV 88 (20% drop from 110)
        # Portfolio value = (50  99) + (100  88) = 4,950 + 8,800 = 13,750 (NAV 916.67 as qty is 150)
        (jan5, Decimal("916.666666")),
    ]

    assert len(result) == len(expected)
    for (date, nav), (exp_date, exp_nav) in zip(result, expected):
        assert date == exp_date
        assert abs(nav - exp_nav) < Decimal("0.1"), f"On {date}, expected NAV {exp_nav} but got {nav}"

    assert len(result2) == len(expected)
    for (date, nav), (exp_date, exp_nav) in zip(result2, expected):
        assert date == exp_date
        assert abs(nav - exp_nav) < Decimal("0.1"), f"On {date}, expected NAV {exp_nav} but got {nav}"

    # Additional assertions to verify portfolio composition
    final_units = defaultdict(Decimal)
    for txn in txns:
        final_units[txn.mf_name] += txn.signed_units()

    assert final_units["MF1"] == Decimal("50")  # Started with 100, sold 50
    assert final_units["MF2"] == Decimal("100")  # Bought 100, no sells


def test_nav_with_full_withdrawal():
    jan1 = datetime.date(2024, 1, 1)
    jan2 = datetime.date(2024, 1, 2)
    jan3 = datetime.date(2024, 1, 3)
    jan4 = datetime.date(2024, 1, 4)

    txns = [
        # Initial investment: 100 units at 100
        Transaction(mf_name="MF1", date=jan1, txn_type=TransactionType.BUY, units=Decimal("100"), nav=Decimal("100")),
        # Value rises 10%, full withdrawal at 110
        Transaction(mf_name="MF1", date=jan2, txn_type=TransactionType.SELL, units=Decimal("100"), nav=Decimal("110")),
        # No holdings on jan3, NAV should stay at 1100
        # Re-entry on jan4, buying 50 units at 120
        Transaction(mf_name="MF1", date=jan4, txn_type=TransactionType.BUY, units=Decimal("50"), nav=Decimal("120")),
    ]

    nav_history = NavManager(
        navs={
            jan1: {"MF1": Decimal("100")},
            jan2: {"MF1": Decimal("110")},
            jan3: {"MF1": Decimal("115")},  # Market keeps moving
            jan4: {"MF1": Decimal("120")},
        },
        current_date=jan4,
    )

    result = calculate_pf_nav(txns, nav_history)
    result2 = calculate_pf_nav2(txns, nav_history)

    # Expected:
    # Jan 1: NAV = 1000 (base)
    # Jan 2: NAV = 1100 (10% up, then full withdrawal)
    # Jan 3: NAV = 1100 (frozen, no holdings)
    # Jan 4: NAV starts at 1100, then reflects performance of new investment

    expected = [
        (jan1, Decimal("1000.0")),
        (jan2, Decimal("1100.0")),
        (jan3, Decimal("1100.0")),
        (jan4, Decimal("1100.0")),  # Initial NAV before processing day's txn
    ]

    assert len(result) == len(expected)
    for (date, nav), (exp_date, exp_nav) in zip(result, expected):
        assert date == exp_date
        assert nav == exp_nav

    assert len(result2) == len(expected)
    for (date, nav), (exp_date, exp_nav) in zip(result2, expected):
        assert date == exp_date
        assert nav == exp_nav, f"On {date}, expected NAV {exp_nav} but got {nav}"
