const API_BASE =
    import.meta.env.VITE_API_BASE_URL ||
    `${window.location.origin}`

async function handleJson(response) {
    if (!response.ok) {
        const text = await response.text()
        throw new Error(text || `HTTP ${response.status}`)
    }
    return response.json()
}

async function apiFetch(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
        credentials: 'include',
        ...options,
        headers: {
            ...(options.headers || {})
        }
    })

    return handleJson(res)
}

export async function newGame() {
    return apiFetch('/api/game/new', {
        method: 'POST'
    })
}

export async function getState() {
    return apiFetch('/api/game/state', {
        method: 'GET'
    })
}

export async function playCard(cardId) {
    return apiFetch('/api/game/play', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ card_id: cardId })
    })
}

export async function giveCard(cardId) {
    return apiFetch('/api/game/give', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ card_id: cardId })
    })
}

export async function chooseContinuation(continueChoice) {
    return apiFetch('/api/game/continue', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ continue_choice: continueChoice })
    })
}

export async function advanceAi() {
    return apiFetch('/api/game/advance', {
        method: 'POST'
    })
}