export default function EventLog({ events }) {
    const items = events ?? []

    return (
        <div style={styles.wrap}>
            <h3 style={styles.heading}>Event log</h3>
            {items.length === 0 ? (
                <div style={styles.empty}>No events yet.</div>
            ) : (
                <ul style={styles.list}>
                    {[...items].reverse().map((item, index) => (
                        <li key={`${index}-${item}`} style={styles.item}>
                            {item}
                        </li>
                    ))}
                </ul>
            )}
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
    empty: {
        color: '#94a3b8'
    },
    list: {
        margin: 0,
        paddingLeft: 18
    },
    item: {
        marginBottom: 8
    }
}