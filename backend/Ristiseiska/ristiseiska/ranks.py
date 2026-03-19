# --- Ristiseiska rank logic ---

LOW_CHAIN = [7, 6, 5, 4, 3, 2, 14]          # 14 = Ace
HIGH_CHAIN = [7, 8, 9, 10, 11, 12, 13]      # 11=J,12=Q,13=K

LOW_NEXT = {LOW_CHAIN[i]: LOW_CHAIN[i + 1] for i in range(len(LOW_CHAIN) - 1)}
HIGH_NEXT = {HIGH_CHAIN[i]: HIGH_CHAIN[i + 1] for i in range(len(HIGH_CHAIN) - 1)}

LOW_PREV = {v: k for k, v in LOW_NEXT.items()}
HIGH_PREV = {v: k for k, v in HIGH_NEXT.items()}


def below_from_7(rank: int) -> int | None:
    """Given a rank on the downward chain, return the next lower rank, else None.
    Example: 7->6, 6->5, 2->A, A->None
    """
    return LOW_NEXT.get(rank)


def above_from_7(rank: int) -> int | None:
    """Given a rank on the upward chain, return the next higher rank, else None.
    Example: 7->8, Q->K, K->None
    """
    return HIGH_NEXT.get(rank)


def is_on_down_chain(rank: int) -> bool:
    return rank in LOW_CHAIN


def is_on_up_chain(rank: int) -> bool:
    return rank in HIGH_CHAIN


def rank_str(rank: int) -> str:
    # Reuse the mapping from cards.py if present; otherwise keep minimal
    return RANK_STR.get(rank, str(rank))
