const API_BASE = 'http://127.0.0.1:8000'

async function handleJson(response) {
    if (!response.ok) {
        const text = await response.text()
        throw new Error(text || `HTTP ${response.status}`)
    }
    return response.json()
}

export async function newGame() {
    const res = await fetch(`${API_BASE}/api/game/new`, {
        method: 'POST'
    })
    return handleJson(res)
}

export async function getState() {
    const res = await fetch(`${API_BASE}/api/game/state`)
    return handleJson(res)
}

export async function playCard(cardId) {
    const res = await fetch(`${API_BASE}/api/game/play`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ card_id: cardId })
    })
    return handleJson(res)
}

export async function giveCard(cardId) {
    const res = await fetch(`${API_BASE}/api/game/give`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ card_id: cardId })
    })
    return handleJson(res)
}

export async function chooseContinuation(continueChoice) {
    const res = await fetch(`${API_BASE}/api/game/continue`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ continue_choice: continueChoice })
    })
    return handleJson(res)
}

export async function advanceAi() {
    const res = await fetch(`${API_BASE}/api/game/advance`, {
        method: 'POST'
    })
    return handleJson(res)
}