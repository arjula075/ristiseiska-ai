import PlayingCard from './PlayingCard'

const suitOrder = ['CLUBS', 'DIAMONDS', 'HEARTS', 'SPADES']
const suitLabels = {
    CLUBS: '♣ Clubs',
    DIAMONDS: '♦ Diamonds',
    HEARTS: '♥ Hearts',
    SPADES: '♠ Spades'
}

const suitSymbols = {
    CLUBS: '♣',
    DIAMONDS: '♦',
    HEARTS: '♥',
    SPADES: '♠'
}

function rankLabel(rank) {
    if (rank === 1) return 'A'
    if (rank === 11) return 'J'
    if (rank === 12) return 'Q'
    if (rank === 13) return 'K'
    return String(rank)
}

function makeTableCard(suit, rank) {
    return {
        id: `table-${suit}-${rank}`,
        suit,
        rank,
        label: `${rankLabel(rank)}${suitSymbols[suit]}`
    }
}

function buildEnds(cards) {
    const normalized = [...cards].sort((a, b) => a - b)
    const has7 = normalized.includes(7)

    if (!has7) {
        return {
            started: false,
            leftEnd: null,
            center: null,
            rightEnd: null
        }
    }

    const left = normalized.filter((rank) => rank >= 1 && rank <= 6)
    const right = normalized.filter((rank) => rank >= 8 && rank <= 13)

    return {
        started: true,
        leftEnd: left.length ? left[0] : null,
        center: 7,
        rightEnd: right.length ? right[right.length - 1] : null
    }
}

function CardOrEmpty({ suit, rank, placeholder }) {
    if (!rank) {
        return <div style={styles.emptyPile}>{placeholder}</div>
    }

    return (
        <PlayingCard
            card={makeTableCard(suit, rank)}
            small
            disabled
        />
    )
}

export default function TableBoard({ table }) {
    const suits = table?.suits ?? []
    const suitMap = new Map(suits.map((row) => [row.suit, row.cards ?? []]))

    return (
        <div style={styles.wrap}>
            <h3 style={styles.heading}>Table</h3>

            {suitOrder.map((suit) => {
                const cards = suitMap.get(suit) ?? []
                const ends = buildEnds(cards)

                return (
                    <div key={suit} style={styles.group}>
                        <div style={styles.groupTitle}>{suitLabels[suit]}</div>

                        <div style={styles.row}>
                            <CardOrEmpty
                                suit={suit}
                                rank={ends.leftEnd}
                                placeholder="—"
                            />

                            {ends.started ? (
                                <PlayingCard
                                    card={makeTableCard(suit, ends.center)}
                                    small
                                    disabled
                                />
                            ) : (
                                <div style={styles.emptyCenter}>7</div>
                            )}

                            <CardOrEmpty
                                suit={suit}
                                rank={ends.rightEnd}
                                placeholder="—"
                            />
                        </div>
                    </div>
                )
            })}
        </div>
    )
}

const styles = {
    wrap: {
        background: '#111827',
        border: '1px solid #334155',
        borderRadius: 12,
        padding: 16,
        marginBottom: 16
    },
    heading: {
        marginTop: 0,
        marginBottom: 12
    },
    group: {
        marginBottom: 14,
        padding: 12,
        border: '1px solid #334155',
        borderRadius: 12,
        background: '#0b1220'
    },
    groupTitle: {
        fontWeight: 700,
        marginBottom: 10
    },
    row: {
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 22,
        minHeight: 92
    },
    emptyPile: {
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 54,
        height: 80,
        borderRadius: 10,
        border: '1px dashed #334155',
        background: '#0f172a',
        color: '#94a3b8',
        fontWeight: 700
    },
    emptyCenter: {
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 54,
        height: 80,
        borderRadius: 10,
        border: '1px dashed #475569',
        background: '#0f172a',
        color: '#cbd5e1',
        fontWeight: 800,
        fontSize: 20
    }
}