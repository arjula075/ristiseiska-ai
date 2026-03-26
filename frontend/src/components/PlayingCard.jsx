import './playing-card.css'

const SUIT_SYMBOLS = {
    CLUBS: '♣',
    DIAMONDS: '♦',
    HEARTS: '♥',
    SPADES: '♠'
}

const RED_SUITS = new Set(['DIAMONDS', 'HEARTS'])

function getRankLabel(card) {
    if (card.rank_label) return card.rank_label
    if (card.label) {
        return card.label.replace(/[♣♦♥♠]/g, '').trim()
    }
    return ''
}

export default function PlayingCard({
                                        card,
                                        onClick,
                                        playable = false,
                                        disabled = false,
                                        small = false
                                    }) {
    const suitSymbol = SUIT_SYMBOLS[card.suit] ?? ''
    const rankLabel = getRankLabel(card)
    const suitColorClass = RED_SUITS.has(card.suit) ? 'suit-red' : 'suit-black'

    const className = [
        'playing-card',
        suitColorClass,
        playable ? 'is-playable' : '',
        disabled ? 'is-disabled' : '',
        small ? 'is-small' : ''
    ]
        .filter(Boolean)
        .join(' ')

    const clickable = !!onClick && !disabled

    return (
        <button
            type="button"
            className={className}
            onClick={clickable ? () => onClick(card) : undefined}
            disabled={!clickable}
            title={card.id}
            aria-label={`${rankLabel}${suitSymbol}`}
        >
            <div className="pc-corner pc-corner-top">
                <div className="pc-rank">{rankLabel}</div>
                <div className="pc-suit">{suitSymbol}</div>
            </div>

            <div className="pc-center">
                <div className="pc-center-rank">{rankLabel}</div>
                <div className="pc-center-suit">{suitSymbol}</div>
            </div>

            <div className="pc-corner pc-corner-bottom">
                <div className="pc-rank">{rankLabel}</div>
                <div className="pc-suit">{suitSymbol}</div>
            </div>
        </button>
    )
}