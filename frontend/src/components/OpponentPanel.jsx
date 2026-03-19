export default function OpponentPanel({ opponent }) {
    return (
        <div
            style={{
                ...styles.card,
                borderColor: opponent.is_active ? '#60a5fa' : '#334155'
            }}
        >
            <div style={styles.title}>Player {opponent.player}</div>
            <div>Cards: {opponent.cards}</div>
            {opponent.is_active && <div style={styles.active}>Active</div>}
        </div>
    )
}

const styles = {
    card: {
        background: '#111827',
        border: '1px solid #334155',
        borderRadius: 12,
        padding: 16,
        minWidth: 140
    },
    title: {
        fontWeight: 700,
        marginBottom: 8
    },
    active: {
        marginTop: 8,
        color: '#93c5fd'
    }
}