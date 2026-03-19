function formatCardId(cardId) {
    if (!cardId) return ''
    const [suit, rank] = cardId.split('-')

    const suitSymbol = {
        CLUBS: '♣',
        DIAMONDS: '♦',
        HEARTS: '♥',
        SPADES: '♠'
    }[suit] || suit

    const rankLabel =
        rank === '1' ? 'A' :
            rank === '11' ? 'J' :
                rank === '12' ? 'Q' :
                    rank === '13' ? 'K' :
                        rank

    return `${rankLabel}${suitSymbol}`
}

export default function StatusBanner({ state, busy, onChooseContinuation }) {
    if (!state) {
        return (
            <div style={styles.banner}>
                No game loaded.
            </div>
        )
    }

    let text = ''
    let showButtons = false

    if (state.game_status === 'no_game') {
        text = 'No active game.'
    } else if (state.ui_mode === 'AI_THINKING') {
        text = `Player ${state.active_player} is thinking...`
    } else if (state.ui_mode === 'PLAY') {
        text = 'Your turn: play a card.'
    } else if (state.ui_mode === 'GIVE') {
        text = 'You are being asked to give a card.'
    } else if (state.ui_mode === 'CONTINUE') {

        showButtons = true

        if (state.pending_play_card_id) {
            const card = formatCardId(state.pending_play_card_id)
            text = `Continue after playing ${card}?`
        } else if (state.pending_continuation) {
            text = 'Do you want to continue?'
        } else {
            text = 'Choose whether to continue.'
        }

    } else if (state.ui_mode === 'GAME_OVER') {
        text = 'Game over.'
    } else {
        text = 'Game state active.'
    }

    if (busy) {
        text += ' Working...'
    }

    return (
        <div style={styles.banner}>
            <div>{text}</div>

            {showButtons && (
                <div style={styles.buttonRow}>
                    <button
                        style={styles.primaryButton}
                        disabled={busy}
                        onClick={() => onChooseContinuation(true)}
                    >
                        Continue
                    </button>

                    <button
                        style={styles.secondaryButton}
                        disabled={busy}
                        onClick={() => onChooseContinuation(false)}
                    >
                        Stop
                    </button>
                </div>
            )}

            {state.error && (
                <div style={styles.error}>{state.error}</div>
            )}
        </div>
    )
}

const styles = {
    banner: {
        background: '#1e293b',
        border: '1px solid #334155',
        borderRadius: 12,
        padding: 16,
        marginBottom: 16
    },
    buttonRow: {
        marginTop: 12,
        display: 'flex',
        gap: 8
    },
    primaryButton: {
        background: '#2563eb',
        border: 'none',
        color: 'white',
        padding: '8px 12px',
        borderRadius: 8,
        cursor: 'pointer'
    },
    secondaryButton: {
        background: '#334155',
        border: '1px solid #475569',
        color: 'white',
        padding: '8px 12px',
        borderRadius: 8,
        cursor: 'pointer'
    },
    error: {
        color: '#fca5a5',
        marginTop: 8
    }
}