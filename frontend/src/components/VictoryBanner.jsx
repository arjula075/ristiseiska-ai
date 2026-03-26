export default function VictoryBanner({ result }) {
    if (!result) return null

    const toneStyles = {
        win: {
            background: 'linear-gradient(135deg, #14532d, #166534)',
            border: '1px solid #22c55e',
            color: '#ecfdf5'
        },
        lose: {
            background: 'linear-gradient(135deg, #3f1d2e, #581c87)',
            border: '1px solid #a855f7',
            color: '#f5f3ff'
        }
    }

    return (
        <div
            style={{
                ...styles.wrap,
                ...toneStyles[result.tone]
            }}
        >
            <div style={styles.title}>{result.title}</div>
            <div style={styles.text}>{result.text}</div>
        </div>
    )
}

const styles = {
    wrap: {
        borderRadius: 16,
        padding: '18px 20px',
        marginBottom: 16,
        boxShadow: '0 10px 24px rgba(0,0,0,0.25)'
    },
    title: {
        fontSize: 24,
        fontWeight: 800,
        marginBottom: 6
    },
    text: {
        fontSize: 16,
        opacity: 0.95
    }
}