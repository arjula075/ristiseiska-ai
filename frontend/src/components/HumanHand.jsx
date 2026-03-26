import PlayingCard from './PlayingCard'

const suitOrder = ['CLUBS', 'DIAMONDS', 'HEARTS', 'SPADES']
const suitLabels = {
    CLUBS: '♣ Clubs',
    DIAMONDS: '♦ Diamonds',
    HEARTS: '♥ Hearts',
    SPADES: '♠ Spades'
}

export default function HumanHand({ hand, state, busy, onCardClick }) {
    const grouped = suitOrder.map((suit) => ({
        suit,
        cards: hand.filter((card) => card.suit === suit)
    }))

    const clickable =
        (state?.ui_mode === 'PLAY' || state?.ui_mode === 'GIVE') &&
        state?.ui_mode !== 'CONTINUE' &&
        !state?.pending_play_card_id &&
        !state?.pending_continuation

    const playableIds = new Set(state?.playable_card_ids ?? [])

    return (
        <div style={styles.wrap}>
            <h3 style={styles.heading}>Your hand</h3>

            {grouped.map((group) => (
                <div key={group.suit} style={styles.group}>
                    <div style={styles.groupTitle}>{suitLabels[group.suit]}</div>

                    <div style={styles.row}>
                        {group.cards.length === 0 ? (
                            <span style={styles.empty}>—</span>
                        ) : (
                            group.cards.map((card) => {
                                const playable =
                                    clickable &&
                                    !busy &&
                                    playableIds.has(card.id)

                                return (
                                    <PlayingCard
                                        key={card.id}
                                        card={card}
                                        playable={playable}
                                        disabled={!playable}
                                        onClick={onCardClick}
                                    />
                                )
                            })
                        )}
                    </div>
                </div>
            ))}
        </div>
    )
}

const styles = {
    wrap: {
        background: '#111827',
        border: '1px solid #334155',
        borderRadius: 12,
        padding: 16
    },
    heading: {
        marginTop: 0,
        marginBottom: 12
    },
    group: {
        marginBottom: 16
    },
    groupTitle: {
        fontWeight: 700,
        marginBottom: 8
    },
    row: {
        display: 'flex',
        gap: 10,
        flexWrap: 'wrap',
        alignItems: 'flex-start'
    },
    empty: {
        color: '#94a3b8'
    }
}