import { useEffect, useMemo, useRef, useState } from 'react'
import {
    advanceAi,
    chooseContinuation,
    getState,
    giveCard,
    newGame,
    playCard
} from './api'
import StatusBanner from './components/StatusBanner'
import OpponentPanel from './components/OpponentPanel'
import TableBoard from './components/TableBoard'
import HumanHand from './components/HumanHand'
import EventLog from './components/EventLog'

const AI_DELAY_MS = 600

export default function App() {
    const [state, setState] = useState(null)
    const [busy, setBusy] = useState(false)
    const [clientError, setClientError] = useState('')
    const aiLoopRunningRef = useRef(false)

    async function refreshState() {
        try {
            const next = await getState()
            setState(next)
        } catch (err) {
            setClientError(String(err))
        }
    }

    async function handleNewGame() {
        setBusy(true)
        setClientError('')
        try {
            const next = await newGame()
            setState(next)
        } catch (err) {
            setClientError(String(err))
        } finally {
            setBusy(false)
        }
    }

    async function handleCardClick(card) {
        if (!state) return
        if (busy) return

        setBusy(true)
        setClientError('')

        try {
            let next

            if (state.ui_mode === 'PLAY') {
                next = await playCard(card.id)
            } else if (state.ui_mode === 'GIVE') {
                next = await giveCard(card.id)
            } else {
                setBusy(false)
                return
            }

            setState(next)
        } catch (err) {
            setClientError(String(err))
        } finally {
            setBusy(false)
        }
    }

    async function handleContinuation(choice) {
        if (busy) return

        setBusy(true)
        setClientError('')

        try {
            const next = await chooseContinuation(choice)
            setState(next)
        } catch (err) {
            setClientError(String(err))
        } finally {
            setBusy(false)
        }
    }

    useEffect(() => {
        refreshState()
    }, [])

    useEffect(() => {
        if (!state) return
        if (busy) return
        if (aiLoopRunningRef.current) return
        if (state.game_status !== 'active') return
        if (state.ui_mode !== 'AI_THINKING') return

        aiLoopRunningRef.current = true

        let cancelled = false

        async function runAiLoop() {
            try {
                let current = state

                while (!cancelled && current?.ui_mode === 'AI_THINKING') {
                    await new Promise((resolve) => setTimeout(resolve, AI_DELAY_MS))
                    const next = await advanceAi()
                    current = next
                    setState(next)
                }
            } catch (err) {
                if (!cancelled) {
                    setClientError(String(err))
                }
            } finally {
                aiLoopRunningRef.current = false
            }
        }

        runAiLoop()

        return () => {
            cancelled = true
        }
    }, [state, busy])

    const mergedError = useMemo(() => {
        return clientError || state?.error || ''
    }, [clientError, state])

    return (
        <div style={styles.page}>
            <div style={styles.container}>
                <h1 style={styles.title}>Ristiseiska</h1>

                <div style={styles.controls}>
                    <button
                        type="button"
                        onClick={handleNewGame}
                        disabled={busy}
                        style={styles.primaryButton}
                    >
                        New game
                    </button>
                </div>

                <StatusBanner
                    state={state ? { ...state, error: mergedError || null } : null}
                    busy={busy}
                    onChooseContinuation={handleContinuation}
                />

                <div style={styles.opponentsRow}>
                    {(state?.opponents ?? []).map((opponent) => (
                        <OpponentPanel key={opponent.player} opponent={opponent} />
                    ))}
                </div>

                <TableBoard table={state?.table} />

                <div style={styles.bottomGrid}>
                    <HumanHand
                        hand={state?.human_hand ?? []}
                        state={state}
                        busy={busy}
                        onCardClick={handleCardClick}
                    />
                    <EventLog events={state?.recent_events ?? []} />
                </div>
            </div>
        </div>
    )
}

const styles = {
    page: {
        minHeight: '100vh',
        background: '#0f172a',
        color: '#e5e7eb',
        padding: 24
    },
    container: {
        maxWidth: 1200,
        margin: '0 auto'
    },
    title: {
        marginTop: 0,
        marginBottom: 16
    },
    controls: {
        marginBottom: 16
    },
    opponentsRow: {
        display: 'flex',
        gap: 12,
        flexWrap: 'wrap',
        marginBottom: 16
    },
    bottomGrid: {
        display: 'grid',
        gridTemplateColumns: '2fr 1fr',
        gap: 16,
        alignItems: 'start'
    },
    primaryButton: {
        background: '#2563eb',
        color: 'white',
        border: 'none',
        borderRadius: 10,
        padding: '10px 14px'
    }
}