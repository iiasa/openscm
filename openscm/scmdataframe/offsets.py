"""
A simplified version of :class:`pandas.DateOffset`s which use datetime-like
objects instead of :class:`pandas.Timestamp`.

This differentiation allows for times which exceed the range of :class`pandas.Timestamp`
(see `here <https://stackoverflow.com/a/37226672>`__) which is particularly important
for longer running models.

TODO: use np.timedelta64 instead?
"""
import datetime
import functools
from typing import Any, Iterable

import pandas as pd
from pandas.tseries.frequencies import to_offset as pd_to_offset
from pandas.tseries.offsets import (
    BusinessMixin,
    DateOffset,
    NaT,
    as_datetime,
    conversion,
    normalize_date,
)


def apply_dt(func, self):
    """
    Apply a wrapper which keeps the result as a datetime instead of converting to
    :class:`pd.Timestamp`.

    This decorator is a simplified version of
    :func:`pandas.tseries.offsets.apply_wraps`. It is required to avoid running into
    errors when our time data is outside panda's limited time range of 1677-09-22
    00:12:43.145225 to 2262-04-11 23:47:16.854775807, see `this discussion
    <https://stackoverflow.com/a/37226672>`_.
    """
    # should self be renamed in the function signature to something else, `ipt`?
    @functools.wraps(func)
    def wrapper(other: datetime.datetime) -> Any:
        if pd.isnull(other):
            return NaT

        tz = getattr(other, "tzinfo", None)

        result = func(self, as_datetime(other))

        if self.normalize:
            # normalize_date returns normal datetime
            result = normalize_date(result)

        if tz is not None and result.tzinfo is None:
            result = conversion.localize_pydatetime(  # pylint: disable=c-extension-no-member  # pragma: no cover
                result, tz
            )

        return result

    return wrapper


def apply_rollforward(obj):
    """
    Roll provided date forward to next offset, only if not on offset.
    """
    # custom wrapper
    def wrapper(dt: datetime.datetime) -> datetime.datetime:
        dt = as_datetime(dt)
        if not obj.onOffset(dt):
            dt = dt + obj.__class__(1, normalize=obj.normalize, **obj.kwds)
        return as_datetime(dt)  # type: ignore # pandas doesn't have type annotations

    return wrapper


def apply_rollback(obj):
    """
    Roll provided date backward to previous offset, only if not on offset.
    """
    # custom wrapper
    def wrapper(dt: datetime.datetime) -> datetime.datetime:
        dt = as_datetime(dt)
        if not obj.onOffset(dt):
            dt = dt - obj.__class__(1, normalize=obj.normalize, **obj.kwds)
        return as_datetime(dt)  # type: ignore # pandas doesn't have type annotations

    return wrapper


def to_offset(rule: str) -> DateOffset:
    """
    Return a wrapped :class:`DateOffset` instance for a given rule.

    The :class:`DateOffset` class is manipulated to return datetimes instead of
    :class:`pd.Timestamp`, allowing it to handle times outside panda's limited time
    range of 1677-09-22 00:12:43.145225 to 2262-04-11 23:47:16.854775807, see `this
    discussion <https://stackoverflow.com/a/37226672>`_.

    Parameters
    ----------
    rule
        The rule to use to generate the offset. For options see `pandas offset aliases
        <http://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#timeseries-offset-aliases>`_.

    Returns
    -------
    :class:`DateOffset`
        Wrapped :class:`DateOffset` class for the given rule

    Raises
    ------
    ValueError
        If unsupported offset rule is requested, e.g. all business related offsets
    """
    offset = pd_to_offset(rule)

    if isinstance(offset, BusinessMixin) or offset.rule_code.startswith("B"):
        raise ValueError(
            "Invalid rule for offset - Business related offsets are not supported"
        )

    def wrap_funcs(fname):
        # Checks if the function has been wrapped and replace with `apply_dt` wrapper
        func = getattr(offset, fname)

        if hasattr(func, "__wrapped__"):  # pragma: no cover
            orig_func = func.__wrapped__
            object.__setattr__(offset, fname, apply_dt(orig_func, offset))

    wrap_funcs("apply")
    object.__setattr__(offset, "rollforward", apply_rollforward(offset))
    object.__setattr__(offset, "rollback", apply_rollback(offset))

    return offset


def generate_range(
    start: datetime.datetime, end: datetime.datetime, offset: DateOffset
) -> Iterable[datetime.datetime]:
    """
    Generate a range of datetime objects between start and end, using offset to
    determine the steps.

    The range will extend both ends of the span to the next valid timestep, see
    examples.

    Parameters
    ----------
    start
        Starting datetime from which to generate the range (noting roll backward
        mentioned above and illustrated in the examples).

    end
        Last datetime from which to generate the range (noting roll forward mentioned
        above and illustrated in the examples).

    offset
        Offset object for determining the timesteps. An offsetter obtained from
        :func`to_offset` *must* be used.

    Yields
    ------
    :obj:`datetime.datetime`
        Next datetime in the range

    Raises
    ------
    ValueError
        Offset does not result in increasing :class`datetime.datetime`s

    Examples
    --------
    The range is extended at either end to the nearest timestep. In the example below,
    the first timestep is rolled back to 1st Jan 2001 whilst the last is extended to 1st
    Jan 2006.

    >>> import datetime as dt
    >>> from pprint import pprint
    >>> from openscm.scmdataframe.offsets import to_offset, generate_range
    >>> g = generate_range(
    ...     dt.datetime(2001, 4, 1),
    ...     dt.datetime(2005, 6, 3),
    ...     to_offset("AS"),
    ... )

    >>> pprint([d for d in g])
    [datetime.datetime(2001, 1, 1, 0, 0),
     datetime.datetime(2002, 1, 1, 0, 0),
     datetime.datetime(2003, 1, 1, 0, 0),
     datetime.datetime(2004, 1, 1, 0, 0),
     datetime.datetime(2005, 1, 1, 0, 0),
     datetime.datetime(2006, 1, 1, 0, 0)]

    In this example the first timestep is rolled back to 31st Dec 2000 whilst the last
    is extended to 31st Dec 2005.

    >>> g = generate_range(
    ...     dt.datetime(2001, 4, 1),
    ...     dt.datetime(2005, 6, 3),
    ...     to_offset("A"),
    ... )
    >>> pprint([d for d in g])
    [datetime.datetime(2000, 12, 31, 0, 0),
     datetime.datetime(2001, 12, 31, 0, 0),
     datetime.datetime(2002, 12, 31, 0, 0),
     datetime.datetime(2003, 12, 31, 0, 0),
     datetime.datetime(2004, 12, 31, 0, 0),
     datetime.datetime(2005, 12, 31, 0, 0)]

    In this example the first timestep is already on the offset so stays there, the last
    timestep is to 1st Sep 2005.

    >>> g = generate_range(
    ...     dt.datetime(2001, 4, 1),
    ...     dt.datetime(2005, 6, 3),
    ...     to_offset("QS"),
    ... )
    >>> pprint([d for d in g])
    [datetime.datetime(2001, 4, 1, 0, 0),
     datetime.datetime(2001, 7, 1, 0, 0),
     datetime.datetime(2001, 10, 1, 0, 0),
     datetime.datetime(2002, 1, 1, 0, 0),
     datetime.datetime(2002, 4, 1, 0, 0),
     datetime.datetime(2002, 7, 1, 0, 0),
     datetime.datetime(2002, 10, 1, 0, 0),
     datetime.datetime(2003, 1, 1, 0, 0),
     datetime.datetime(2003, 4, 1, 0, 0),
     datetime.datetime(2003, 7, 1, 0, 0),
     datetime.datetime(2003, 10, 1, 0, 0),
     datetime.datetime(2004, 1, 1, 0, 0),
     datetime.datetime(2004, 4, 1, 0, 0),
     datetime.datetime(2004, 7, 1, 0, 0),
     datetime.datetime(2004, 10, 1, 0, 0),
     datetime.datetime(2005, 1, 1, 0, 0),
     datetime.datetime(2005, 4, 1, 0, 0),
     datetime.datetime(2005, 7, 1, 0, 0)]
    """
    # Get the bounds
    start = offset.rollback(start)
    end = offset.rollforward(end)

    # Iterate to find all the required timesteps
    current = start
    while current <= end:
        yield current

        next_current = offset.apply(current)
        if next_current <= current:
            raise ValueError(  # pragma: no cover  # emergency valve
                "Offset is not increasing datetime: {}".format(current.isoformat())
            )

        current = next_current
