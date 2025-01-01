import enum
from dataclasses import dataclass
from decimal import Decimal
import datetime
from collections import defaultdict
from typing import List, Tuple, Dict


class TxnType(enum.Enum):
    BUY: str = 'BUY'
    SELL: str = 'SELL'


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


def calculate_pf_nav(
        txns: List[MfTxn],
        nav_history: NavHistory,
        base_nav: Decimal = Decimal('1000.0')
) -> List[Tuple[datetime.date, Decimal]]:
    """Calculate portfolio NAV for all transaction dates and current date."""
    curr_holdings: Dict[str, Decimal] = defaultdict(Decimal)
    pf_navs: List[Tuple[datetime.date, Decimal]] = []
    txn_dates: List[datetime.date] = sorted(set(txn.date for txn in txns))
    txns_by_date: Dict[datetime.date, List[MfTxn]] = defaultdict(list)
    for txn in txns:
        txns_by_date[txn.date].append(txn)

    # Process first date - establish baseline
    first_date: datetime.date = txn_dates[0]
    for txn in txns_by_date[first_date]:
        delta: Decimal = txn.units if txn.txn_type == TxnType.BUY else -txn.units
        curr_holdings[txn.mf_name] += delta

    initial_value: Decimal = sum(  # noqa
        curr_holdings[fund] * nav_history.navs[first_date][fund]
        for fund in curr_holdings
        if curr_holdings[fund] != 0
    )
    pf_navs.append((first_date, base_nav))

    # Process remaining dates
    for date in txn_dates[1:]:
        # Calculate current value before today's transactions
        curr_value: Decimal = sum(  # noqa
            curr_holdings[fund] * nav_history.navs[date][fund]
            for fund in curr_holdings
            if curr_holdings[fund] != 0
        )

        normalized_nav: Decimal = (curr_value / initial_value) * base_nav
        pf_navs.append((date, normalized_nav))

        # Process today's transactions
        for txn in txns_by_date[date]:
            delta = txn.units if txn.txn_type == TxnType.BUY else -txn.units
            curr_holdings[txn.mf_name] += delta

            # Adjust initial_value to maintain relative growth
            if txn.txn_type == TxnType.BUY:
                # New investment's "initial value" should be proportional to current NAV
                initial_value += (delta * txn.nav) / normalized_nav * base_nav
            else:
                # For sells, reduce initial_value proportionally
                initial_value -= (delta * txn.nav) / normalized_nav * base_nav

    if nav_history.current_date > txn_dates[-1]:
        curr_value = sum(  # noqa
            curr_holdings[fund] * nav_history.navs[nav_history.current_date][fund]
            for fund in curr_holdings
            if curr_holdings[fund] != 0
        )
        normalized_nav = (curr_value / initial_value) * base_nav
        pf_navs.append((nav_history.current_date, normalized_nav))

    return pf_navs
