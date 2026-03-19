const suitLabels = {
    CLUBS: '♣ Clubs',
    DIAMONDS: '♦ Diamonds',
    HEARTS: '♥ Hearts',
    SPADES: '♠ Spades'
}

function rankLabel(rank) {
    if (rank == null) return '—'
    if (rank === 1) return 'A'
    if (rank === 11) return 'J'
    if (rank === 12) return 'Q'
    if (rank === 13) return 'K'
    return String(rank)
}

function getSuitEnds(cards) {
    const ranks = Array.isArray(cards) ? [...cards].sort((a, b) => a - b) : []
    const hasSeven = ranks.includes(7)

    if (!hasSeven) {
        return {
            low: null,
            center: null,
            high: null
        }
    }

    const lowCards = ranks.filter((r) => r < 7)
    const highCards = ranks.filter((r) => r > 7)

    return {
        low: lowCards.length > 0 ? Math.min(...lowCards) : null,
        center: 7,
        high: highCards.length > 0 ? Math.max(...highCards) : null
    }
}

function EndSlot({ value, active }) {
    return (
        <span
            style={{
                ...styles.slot,
                ...(active ? styles.slotFilled : styles.slotEmpty)
            }}
        >
            {rankLabel(value)}
        </span>
    )
}

function SuitRow({ suit }) {
    const { low, center, high } = getSuitEnds(suit.cards)

    return (
        <div style={styles.suitCard}>
            <div style={styles.suitTitle}>
                {suitLabels[suit.suit] ?? suit.suit}
            </div>

            <div style={styles.tripletRow}>
                <EndSlot value={low} active={low != null} />
                <EndSlot value={center} active={center != null} />
                <EndSlot value={high} active={high != null} />
            </div>
        </div>
    )
}

export default function TableBoard({ table }) {
    console.log('TABLE DATA', JSON.stringify(table, null, 2))
    const suits = table?.suits ?? []

    return (
        <div style={styles.wrap}>
            <h3 style={styles.heading}>Table</h3>
            <div style={styles.grid}>
                {suits.map((suit) => (
                    <SuitRow key={suit.suit} suit={suit} />
                ))}
            </div>
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
    grid: {
        display: 'grid',
        gap: 12
    },
    suitCard: {
        background: '#0b1220',
        border: '1px solid #334155',
        borderRadius: 10,
        padding: 12
    },
    suitTitle: {
        fontWeight: 700,
        marginBottom: 8
    },
    tripletRow: {
        display: 'flex',
        alignItems: 'center',
        gap: 12
    },
    slot: {
        minWidth: 42,
        textAlign: 'center',
        borderRadius: 8,
        padding: '8px 12px',
        border: '1px solid #475569',
        fontWeight: 600,
        boxSizing: 'border-box'
    },
    slotFilled: {
        background: '#1f2937',
        color: '#f8fafc',
        opacity: 1
    },
    slotEmpty: {
        background: '#0f172a',
        color: '#64748b',
        opacity: 0.55
    }
}