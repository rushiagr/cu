from decimal import Decimal
import datetime

from pfnav import calculate_pf_nav
from pfnav import MfTxn
from pfnav import NavHistory
from pfnav import TxnType


def test_portfolio_nav_calculation():
    # Setup test data
    jan1 = datetime.date(2024, 1, 1)
    jan2 = datetime.date(2024, 1, 2)
    jan3 = datetime.date(2024, 1, 3)
    jan4 = datetime.date(2024, 1, 4)

    # Transactions
    txns = [
        MfTxn(
            mf_name="MF1",
            date=jan1,
            txn_type=TxnType.BUY,
            units=Decimal('100'),
            nav=Decimal('100')  # Though nav is in txn, we'll use nav_history
        ),
        MfTxn(
            mf_name="MF2",
            date=jan2,
            txn_type=TxnType.BUY,
            units=Decimal('100'),
            nav=Decimal('110')
        )
    ]

    # NAV history including all dates and funds
    nav_history = NavHistory(
        navs={
            jan1: {
                "MF1": Decimal('100'),
                "MF2": Decimal('100')  # Not used but available
            },
            jan2: {
                "MF1": Decimal('110'),
                "MF2": Decimal('110')
            },
            jan3: {
                "MF1": Decimal('121'),
                "MF2": Decimal('132')
            },
            jan4: {
                "MF1": Decimal('110'),
                "MF2": Decimal('110')
            },
        },
        current_date=jan4
    )

    # Calculate portfolio NAV
    result = calculate_pf_nav(txns, nav_history)

    # Expected values based on your example:
    # Jan 1: Base NAV = 1000
    # Jan 2: 10% increase = 1100
    # Jan 3: 15% increase from 1100 = 1265
    # Jan 4: back to 1100

    expected = [
        (jan1, Decimal('1000.0')),
        (jan2, Decimal('1100.0')),
        (jan3, Decimal('1265.0')),
        (jan4, Decimal('1100.0')),
    ]

    assert len(result) == len(expected)
    for (date, nav), (exp_date, exp_nav) in zip(result, expected):
        assert date == exp_date
        assert nav == exp_nav, f"On {date}, expected NAV {exp_nav} but got {nav}"
