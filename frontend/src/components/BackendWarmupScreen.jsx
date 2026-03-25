export default function BackendWarmupScreen({ phase }) {
    let text = "Yhdistetään palveluun...";

    if (phase === "warming") {
        text = "Pelipalvelu herää. Ensimmäinen käynnistys voi kestää hetken.";
    } else if (phase === "timeout") {
        text = "Palvelu ei käynnistynyt ajoissa. Päivitä sivu ja yritä uudelleen.";
    } else if (phase === "error") {
        text = "Palveluun ei saada yhteyttä juuri nyt.";
    }

    return (
        <div className="min-h-screen flex items-center justify-center p-6">
            <div className="max-w-md text-center">
                <h1 className="text-2xl font-semibold mb-4">Ristiseiska AI</h1>
                <p>{text}</p>
            </div>
        </div>
    );
}