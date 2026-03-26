import { useEffect, useMemo, useRef, useState } from 'react'
import {
    advanceAi,
    chooseContinuation,
    getState,
    giveCard,
    newGame,
    playCard
} from './api'
import BackendWarmupScreen from './components/BackendWarmupScreen'
import StatusBanner from './components/StatusBanner'
import OpponentPanel from './components/OpponentPanel'
import TableBoard from './components/TableBoard'
import HumanHand from './components/HumanHand'
import EventLog from './components/EventLog'
import EventBanner from './components/EventBanner'
import VictoryBanner from './components/VictoryBanner'

const AI_DELAY_MS = 600
const READY_POLL_INTERVAL_MS = 2000
const READY_MAX_ATTEMPTS = 30
const BACKEND_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export default function App() {
    const [state, setState] = useState(null)
    const [busy, setBusy] = useState(false)
    const [clientError, setClientError] = useState('')
    const [backendPhase, setBackendPhase] = useState('starting') // starting | warming | ready | timeout | error
    const aiLoopRunningRef = useRef(false)
    const [eventBanner, setEventBanner] = useState(null)
    const previousOpponentsRef = useRef([])
    const previousEventsRef = useRef([])
    const [victoryBanner, setVictoryBanner] = useState(null)

    async function checkBackendReady() {
        console.log(BACKEND_URL)
        const res = await fetch(`${BACKEND_URL}/ready`, {
            method: 'GET',
            credentials: 'include'
        })

        if (res.ok) {
            return { ready: true }
        }

        if (res.status === 503) {
            return { ready: false, warming: true }
        }

        return { ready: false, warming: false }
    }

    async function refreshState() {
        try {
            const next = await getState()
            setState(next)
        } catch (err) {
            setClientError(String(err))
        }
    }

    async function handleNewGame() {
        if (backendPhase !== 'ready') return

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
        if (backendPhase !== 'ready') return
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
        if (backendPhase !== 'ready') return
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
        if (!state) return

        const currentEvents = state.recent_events ?? []
        const previousEvents = previousEventsRef.current
        const latestEvent = currentEvents[currentEvents.length - 1]

        // 1) Sinä jouduit ottamaan kortin
        if (
            latestEvent &&
            latestEvent !== previousEvents[previousEvents.length - 1] &&
            latestEvent.includes('You cannot play. Requesting a card...')
        ) {
            setEventBanner({
                message: 'Voi ei — jouduit ottamaan kortin.',
                tone: 'warning'
            })
        }

        // 2) Tietokonepelaaja pääsi pois
        const prevOpponents = previousOpponentsRef.current
        const currentOpponents = state.opponents ?? []

        for (const current of currentOpponents) {
            const prev = prevOpponents.find((p) => p.player === current.player)

            if (prev && prev.cards > 0 && current.cards === 0) {
                setEventBanner({
                    message: `Pelaaja ${current.player} pääsi pois — nyt pelataan enää sijoista.`,
                    tone: 'danger'
                })
                break
            }
        }

        previousEventsRef.current = currentEvents
        previousOpponentsRef.current = currentOpponents
    }, [state])

    useEffect(() => {
        let cancelled = false

        async function waitUntilReady() {
            for (let i = 0; i < READY_MAX_ATTEMPTS; i += 1) {
                try {
                    const result = await checkBackendReady()

                    if (cancelled) return

                    if (result.ready) {
                        setBackendPhase('ready')
                        await refreshState()
                        return
                    }

                    if (result.warming) {
                        setBackendPhase('warming')
                    } else {
                        setBackendPhase('error')
                    }
                } catch (err) {
                    if (!cancelled) {
                        setBackendPhase('starting')
                    }
                }

                await new Promise((resolve) =>
                    setTimeout(resolve, READY_POLL_INTERVAL_MS)
                )
            }

            if (!cancelled) {
                setBackendPhase('timeout')
            }
        }

        waitUntilReady()

        return () => {
            cancelled = true
        }
    }, [])

    useEffect(() => {
        if (!eventBanner) return

        const timer = setTimeout(() => {
            setEventBanner(null)
        }, 3000)

        return () => clearTimeout(timer)
    }, [eventBanner])

    useEffect(() => {
        if (!state) return

        if (state.game_status !== 'game_over') {
            setVictoryBanner(null)
            return
        }

        const winner = (state.opponents ?? []).find((opponent) => opponent.cards === 0)
        const humanCards = state.human_hand?.length ?? 0

        if (winner) {
            setVictoryBanner({
                tone: 'lose',
                title: `Pelaaja ${winner.player} voitti`,
                text: 'Sinä et ehtinyt ensimmäisenä ulos.'
            })
            return
        }

        if (humanCards === 0) {
            setVictoryBanner({
                tone: 'win',
                title: 'Voitto!',
                text: 'Pääsit ensimmäisenä eroon korteistasi.'
            })
            return
        }

        setVictoryBanner({
            tone: 'lose',
            title: 'Peli päättyi',
            text: 'Voittajaa ei saatu pääteltyä käyttöliittymässä.'
        })
    }, [state])

    useEffect(() => {
        if (backendPhase !== 'ready') return
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

                while (
                    !cancelled &&
                    current?.ui_mode === 'AI_THINKING' &&
                    backendPhase === 'ready'
                    ) {
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
    }, [state, busy, backendPhase])

    const mergedError = useMemo(() => {
        return clientError || state?.error || ''
    }, [clientError, state])

    if (backendPhase !== 'ready') {
        return <BackendWarmupScreen phase={backendPhase} />
    }

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

                <div style={styles.gameLayout}>
                    <div style={styles.tableOuter}>
                        <div style={styles.tableInner}>
                            <TableBoard table={state?.table} />
                        </div>
                        {victoryBanner && <VictoryBanner result={victoryBanner} />}

                        {eventBanner && (
                            <EventBanner
                                message={eventBanner.message}
                                tone={eventBanner.tone}
                            />
                        )}
                    </div>


                    <div style={styles.sideColumn}>
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
        </div>
    )
}

const styles = {
    tableOuter: {
        width: '100%'
    },

    tableInner: {
        width: '100%',
        display: 'grid',
        gap: 12
    },

    page: {
        minHeight: '100vh',
        background: '#0f172a',
        color: '#e5e7eb',
        padding: 24
    },

    container: {
        maxWidth: 1440,
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

    gameLayout: {
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 2fr) minmax(320px, 420px)',
        gap: 16,
        alignItems: 'start'
    },

    mainColumn: {
        minWidth: 0
    },

    sideColumn: {
        minWidth: 0,
        display: 'grid',
        gap: 16,
        alignContent: 'start'
    },

    primaryButton: {
        background: '#2563eb',
        color: 'white',
        border: 'none',
        borderRadius: 10,
        padding: '10px 14px'
    }
}