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


def calculate_pf_nav2(
    txns: List[MfTxn], nav_history: NavHistory, base_nav: Decimal = Decimal("1000.0")
) -> List[Tuple[datetime.date, Decimal]]:
    """Calculate portfolio NAV for all possible dates.

    'unit-based' method discussed here: https://forum.valuepickr.com/t/how-to-track-ones-portfolio-effectively/564/5
        text copied: https://gist.github.com/rushiagr/1bb9f6433f6610952972c88364e9c7ad

    Returns NAVs for all dates in nav_history between first transaction and current_date
    Handles zero-value periods by maintaining last known NAV.
    """
    # curr_units stores current units (as of the last transaction processed) for each mutual fund
    curr_units: DefaultDict[str, Decimal] = defaultdict(Decimal)
    # pf_navs stores the portfolio NAV for each date. This is what gets returned by this func
    pf_navs: List[Tuple[datetime.date, Decimal]] = []
    last_nav = base_nav  # Track last known NAV for zero-value periods

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
            if curr_pf_value == 0 and txn.txn_type == TxnType.BUY:
                # Reset initial_pf_value relative to last known NAV
                initial_pf_value = (txn.units * txn.nav) / last_nav * base_nav
            else:
                # Normal adjustment
                adjustment = (txn.signed_units() * txn.nav) / normalized_nav * base_nav
                initial_pf_value += adjustment

    return pf_navs


def calculate_pf_nav(
    txns: List[MfTxn], nav_history: NavHistory, base_nav: Decimal = Decimal("1000.0")
) -> List[Tuple[datetime.date, Decimal]]:
    """
    Calculate portfolio NAV using blog's unit-based approach.
    During zero-value periods (full withdrawal), NAV remains frozen at last known value.
    """
    portfolio_units = Decimal("0")  # Units in terms of portfolio NAV
    portfolio_holdings = defaultdict(Decimal)  # fund -> actual units of fund
    pf_navs = []
    last_nav = base_nav  # Track last known NAV for zero-value periods

    # Group transactions by date
    txns_by_date = defaultdict(list)
    for txn in txns:
        txns_by_date[txn.date].append(txn)

    # Get sorted dates
    first_txn_date = min(txn.date for txn in txns)
    all_dates = sorted(set(list(nav_history.navs.keys()) + [txn.date for txn in txns]))
    relevant_dates = [date for date in all_dates if first_txn_date <= date <= nav_history.current_date]

    for date in relevant_dates:
        # First calculate NAV based on existing holdings
        portfolio_value = sum(units * nav_history.navs[date][fund] for fund, units in portfolio_holdings.items())

        # If we have units, calculate NAV normally
        if portfolio_units > 0:
            current_nav = portfolio_value / portfolio_units
            last_nav = current_nav  # Remember this NAV
        else:
            # No units - use last known NAV
            current_nav = last_nav

        # Process transactions after NAV calculation (because transactions are considered to have happened at EOD)
        for txn in txns_by_date[date]:
            txn_value = txn.units * txn.nav
            if portfolio_units == 0:
                # First transaction - convert value to portfolio units at base_nav - or re-entry after zero value
                # Use last_nav instead of base_nav for re-entry
                portfolio_units = txn_value / last_nav
            else:
                # Subsequent transactions - convert value to portfolio units at current NAV
                portfolio_units += txn_value / current_nav * txn.sign()

            # Update actual fund holdings
            portfolio_holdings[txn.mf_name] += txn.signed_units()

        pf_navs.append((date, current_nav))

    return pf_navs
