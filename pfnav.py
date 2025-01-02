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

    def signed_units(self) -> Decimal:
        """Return signed units based on transaction type, i.e. positive for BUY and negative for SELL."""
        return self.sign() * self.units

    def sign(self) -> int:
        """Return sign based on transaction type, i.e. +1 for BUY and -1 for SELL."""
        return 1 if self.txn_type == TxnType.BUY else -1


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
    """Calculate portfolio NAV for all possible dates.

    Returns NAVs for all dates in nav_history between first transaction and current_date
    """
    # curr_units stores current units (as of the last transaction processed) for each mutual fund
    curr_units: DefaultDict[str, Decimal] = defaultdict(Decimal)
    # pf_navs stores the portfolio NAV for each date. This is what gets returned by this func
    pf_navs: List[Tuple[datetime.date, Decimal]] = []

    # Get all dates to process (transactions + intermediate dates + current date)
    first_txn_date = min(txn.date for txn in txns)
    all_dates: List[datetime.date] = sorted(set(list(nav_history.navs.keys()) + [txn.date for txn in txns]))
    # Filter dates between first transaction and current date inclusive
    relevant_dates = [date for date in all_dates if first_txn_date <= date <= nav_history.current_date]

    # Group transactions by date for efficient processing
    txns_by_date: Dict[datetime.date, List[MfTxn]] = defaultdict(list)
    for txn in txns:
        txns_by_date[txn.date].append(txn)

    # Process first date - establish baseline
    first_date: datetime.date = relevant_dates[0]
    for txn in txns_by_date[first_date]:
        curr_units[txn.mf_name] += txn.signed_units()

    initial_pf_value: Decimal = _calculate_portfolio_value(curr_units, nav_history.navs[first_date])
    pf_navs.append((first_date, base_nav))

    # Process remaining dates
    for date in relevant_dates[1:]:
        # Calculate value before today's transactions. Today's transactions are processed AFTER today's NAV calculation
        curr_pf_value: Decimal = _calculate_portfolio_value(curr_units, nav_history.navs[date])
        normalized_nav: Decimal = (curr_pf_value / initial_pf_value) * base_nav
        pf_navs.append((date, normalized_nav))

        # Process today's transactions if any. Done after calculating NAV for the day as txns considered happened at EOD
        for txn in txns_by_date[date]:
            curr_units[txn.mf_name] += txn.signed_units()

            # Adjust initial_pf_value to maintain relative growth
            adjustment: Decimal = (txn.signed_units() * txn.nav) / normalized_nav * base_nav
            initial_pf_value += adjustment

    return pf_navs
