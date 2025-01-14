import datetime
import enum
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import DefaultDict, Dict, List, Tuple


class TransactionType(enum.Enum):
    BUY: str = "BUY"
    SELL: str = "SELL"


@dataclass
class Transaction:
    mf_name: str
    date: datetime.date
    txn_type: TransactionType
    units: Decimal
    nav: Decimal

    def signed_units(self) -> Decimal:
        """Return signed units based on transaction type, i.e. positive for BUY and negative for SELL."""
        return self.sign() * self.units

    def sign(self) -> int:
        """Return sign based on transaction type, i.e. +1 for BUY and -1 for SELL."""
        return 1 if self.txn_type == TransactionType.BUY else -1


@dataclass
class NavHistory:
    """Repository of all NAVs of all mutual funds."""

    # navs is a dictionary of NAV date -> fund name -> NAV
    navs: Dict[datetime.date, Dict[str, Decimal]]
    current_date: datetime.date

    def get_all_dates_sorted(self) -> List[datetime.date]:
        return sorted(self.navs.keys())


# Assumptions for calculate_pf_nav() function (TODO: add checks for the same):
#   - transaction dates are sorted in ascending order (i.e. oldest first)
#   - all transaction dates are present in nav_history, i.e. NAV is available for all transaction dates of respective
#     mutual funds


def _calculate_portfolio_value(units: DefaultDict[str, Decimal], navs: Dict[str, Decimal]) -> Decimal:
    """Helper function to calculate portfolio value given units and NAVs."""
    return sum(units[fund] * navs[fund] for fund in units if units[fund] != 0)  # noqa


def calculate_pf_nav2(
    txns: List[Transaction], nav_history: NavHistory, base_nav: Decimal = Decimal("1000.0")
) -> List[Tuple[datetime.date, Decimal]]:
    """Calculate portfolio NAV for all possible dates.

    'unit-based' method discussed here: https://forum.valuepickr.com/t/how-to-track-ones-portfolio-effectively/564/5
        text copied: https://gist.github.com/rushiagr/1bb9f6433f6610952972c88364e9c7ad

    Returns NAVs for all dates in nav_history between first transaction and current_date
    Handles zero-value periods by maintaining last known NAV.
    """

    # basic sanity checks
    if not txns:
        raise ValueError("No transactions provided")

    # curr_units stores current units (as of the last transaction processed) for each mutual fund
    curr_units: DefaultDict[str, Decimal] = defaultdict(Decimal)
    # pf_navs stores the portfolio NAV for each date. This is what gets returned by this func
    pf_navs: List[Tuple[datetime.date, Decimal]] = []
    last_nav = base_nav  # Track last known NAV for zero-value periods

    # Filter dates between first transaction and current date inclusive
    relevant_dates = [
        date for date in nav_history.get_all_dates_sorted() if txns[0].date <= date <= nav_history.current_date
    ]

    # Group transactions by date for efficient processing
    txns_by_date: Dict[datetime.date, List[Transaction]] = defaultdict(list)
    for txn in txns:
        txns_by_date[txn.date].append(txn)

    # Process first date - establish baseline
    first_date: datetime.date = relevant_dates[0]
    for txn in txns_by_date[first_date]:
        curr_units[txn.mf_name] += txn.signed_units()
    pf_navs.append((first_date, base_nav))

    initial_pf_value: Decimal = _calculate_portfolio_value(curr_units, nav_history.navs[first_date])

    # Handle case where initial value is zero (should never happen on first date, but being defensive)
    if initial_pf_value == 0:
        initial_pf_value = Decimal("1.0")  # Arbitrary non-zero value

    # Process remaining dates
    for date in relevant_dates[1:]:
        # Calculate value before today's transactions. Today's transactions are processed AFTER today's NAV calculation
        curr_pf_value: Decimal = _calculate_portfolio_value(curr_units, nav_history.navs[date])

        # If we have holdings, calculate NAV normally
        if curr_pf_value > 0 or initial_pf_value > 0:
            normalized_nav = (curr_pf_value / initial_pf_value) * base_nav
            last_nav = normalized_nav  # Remember this NAV
        else:
            # No holdings - use last known NAV
            normalized_nav = last_nav

        pf_navs.append((date, normalized_nav))

        # Process today's transactions if any. Done after calculating NAV for the day as txns considered happened at EOD
        for txn in txns_by_date[date]:
            curr_units[txn.mf_name] += txn.signed_units()

            # If this is a re-entry after zero value
            if curr_pf_value == 0 and txn.txn_type == TransactionType.BUY:
                # Reset initial_pf_value relative to last known NAV
                initial_pf_value = (txn.units * txn.nav) / last_nav * base_nav
            else:
                # Normal adjustment
                adjustment = (txn.signed_units() * txn.nav) / normalized_nav * base_nav
                initial_pf_value += adjustment

    return pf_navs


def calculate_pf_nav(
    txns: List[Transaction], nav_history: NavHistory, base_nav: Decimal = Decimal("1000.0")
) -> List[Tuple[datetime.date, Decimal]]:
    """
    Calculate portfolio NAV using blog's unit-based approach.
    During zero-value periods (full withdrawal), NAV remains frozen at last known value.
    """

    # basic sanity checks
    if not txns:
        raise ValueError("No transactions provided")

    # Group transactions by date
    # Get sorted dates
    relevant_dates = [
        date for date in nav_history.get_all_dates_sorted() if txns[0].date <= date <= nav_history.current_date
    ]

    if not relevant_dates:
        raise ValueError("No relevant dates found")

    txns_by_date = defaultdict(list)
    for txn in txns:
        txns_by_date[txn.date].append(txn)

    portfolio_units = Decimal("0")  # Units held in portfolio
    portfolio_holdings = defaultdict(Decimal)  # mapping of fund name -> actual units of fund

    pf_navs = []
    last_nav = base_nav  # Track last known NAV for zero-value periods

    for date in relevant_dates:

        if portfolio_units == 0:
            current_nav = last_nav  # if no units left for the given date, then use NAV of last date
        else:
            portfolio_value = sum(units * nav_history.navs[date][fund] for fund, units in portfolio_holdings.items())
            current_nav = portfolio_value / portfolio_units
            last_nav = current_nav  # Remember this NAV

        # Because today's transactions are processed at EOD i.e. AFTER today's NAV calculation, we know today's NAV now
        pf_navs.append((date, current_nav))

        for txn in txns_by_date[date]:
            txn_value = txn.units * txn.nav
            # convert value to portfolio units at current NAV, and add to / subtract from portfolio_units
            portfolio_units += txn_value / current_nav * txn.sign()
            portfolio_holdings[txn.mf_name] += txn.signed_units()

    return pf_navs
