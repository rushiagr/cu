import datetime
import enum
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import DefaultDict, Dict, List, Tuple


class TxnType(enum.Enum):
    BUY: str = "BUY"
    SELL: str = "SELL"


@dataclass
class MfTxn:
    mf_name: str
    date: datetime.date
    txn_type: TxnType
    units: Decimal
    nav: Decimal


@dataclass
class NavHistory:
    """Stores NAV for all mutual funds for all transaction dates and current date"""

    # ASSUMPTION: NAVs are available for all transaction dates and current date, for all funds
    # date -> (mf_name -> nav) mapping
    navs: Dict[datetime.date, Dict[str, Decimal]]
    current_date: datetime.date


def _calculate_portfolio_value(units: DefaultDict[str, Decimal], navs: Dict[str, Decimal]) -> Decimal:
    """Helper function to calculate portfolio value given units and NAVs."""
    return sum(units[fund] * navs[fund] for fund in units if units[fund] != 0)  # noqa


def calculate_pf_nav(
    txns: List[MfTxn], nav_history: NavHistory, base_nav: Decimal = Decimal("1000.0")
) -> List[Tuple[datetime.date, Decimal]]:
    """Calculate portfolio NAV for all transaction dates and current date.

    Returns NAVs for:
    1. All transaction dates
    2. All dates in nav_history between first transaction and current_date
    """
    curr_units: DefaultDict[str, Decimal] = defaultdict(Decimal)
    pf_navs: List[Tuple[datetime.date, Decimal]] = []

    # Get all dates to process (transactions + intermediate dates + current date)
    all_dates: List[datetime.date] = sorted(set(list(nav_history.navs.keys()) + [txn.date for txn in txns]))

    # Filter dates between first transaction and current date inclusive
    first_txn_date = min(txn.date for txn in txns)
    relevant_dates = [date for date in all_dates if first_txn_date <= date <= nav_history.current_date]

    # Group transactions by date for efficient processing
    txns_by_date: Dict[datetime.date, List[MfTxn]] = defaultdict(list)
    for txn in txns:
        txns_by_date[txn.date].append(txn)

    # Process first date - establish baseline
    first_date: datetime.date = relevant_dates[0]
    for txn in txns_by_date[first_date]:
        delta: Decimal = txn.units if txn.txn_type == TxnType.BUY else -txn.units
        curr_units[txn.mf_name] += delta

    initial_value: Decimal = _calculate_portfolio_value(curr_units, nav_history.navs[first_date])
    pf_navs.append((first_date, base_nav))

    # Process remaining dates
    for date in relevant_dates[1:]:
        # Calculate value before today's transactions
        curr_value: Decimal = _calculate_portfolio_value(curr_units, nav_history.navs[date])
        normalized_nav: Decimal = (curr_value / initial_value) * base_nav
        pf_navs.append((date, normalized_nav))

        # Process today's transactions if any
        for txn in txns_by_date[date]:
            delta = txn.units if txn.txn_type == TxnType.BUY else -txn.units
            curr_units[txn.mf_name] += delta

            # Adjust initial_value to maintain relative growth
            adjustment: Decimal = (delta * txn.nav) / normalized_nav * base_nav
            initial_value += adjustment if txn.txn_type == TxnType.BUY else -adjustment

    return pf_navs
