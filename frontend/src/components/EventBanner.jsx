export default function EventBanner({ message, tone = 'info' }) {
    if (!message) return null

    const toneStyles = {
        info: {
            background: '#1e293b',
            border: '1px solid #475569',
            color: '#e2e8f0'
        },
        warning: {
            background: '#3b1d1d',
            border: '1px solid #b45309',
            color: '#fde68a'
        },
        danger: {
            background: '#2a1a3a',
            border: '1px solid #7c3aed',
            color: '#e9d5ff'
        }
    }

    return (
        <div
            style={{
                ...styles.wrap,
                ...toneStyles[tone]
            }}
        >
            {message}
        </div>
    )
}

const styles = {
    wrap: {
        borderRadius: 12,
        padding: '12px 16px',
        marginBottom: 16,
        fontWeight: 700
    }
}