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
            <div className="max-w-2xl text-center space-y-6">
                <h1 className="text-3xl font-semibold">Ristiseiska AI</h1>

                <p className="text-slate-300">{text}</p>

                {phase === "warming" && (
                    <div className="text-left bg-slate-900 border border-slate-700 rounded-xl p-6 space-y-5">
                        <div>
                            <h2 className="text-lg font-semibold mb-2">Valmistellaan peliä…</h2>
                            <p className="text-sm text-slate-300">
                                Palvelu käynnistyy juuri nyt. Koska käytössä on ilmainen palvelin (Render),
                                se menee välillä lepotilaan ja herää ensimmäisestä pyynnöstä.
                                Tämä voi kestää muutaman sekunnin.
                            </p>
                        </div>

                        <div>
                            <h3 className="font-semibold mb-2">Peli lyhyesti</h3>
                            <ul className="text-sm text-slate-300 space-y-1 list-disc list-inside">
                                <li><strong>Tavoite:</strong> pääse ensimmäisenä eroon korteistasi.</li>
                                <li>Pöytä alkaa seiskoista.</li>
                                <li>Samaa maata jatketaan molempiin suuntiin.</li>
                                <li>Alaspäin: 6 → 5 → 4 → 3 → 2 → A</li>
                                <li>Ylöspäin: 8 → 9 → 10 → J → Q → K</li>
                                <li>Jos et voi pelata, joudut pyytämään kortin.</li>
                                <li>Jos toinen pelaaja pyytää, sinulta voidaan pyytää kortti annettavaksi.</li>
                            </ul>
                        </div>

                        <div>
                            <h3 className="font-semibold mb-2">Näin pelaat</h3>
                            <ul className="text-sm text-slate-300 space-y-1 list-disc list-inside">
                                <li>Vihreällä korostettu kortti on pelattavissa.</li>
                                <li>Klikkaa korttia pelataksesi tai antaaksesi sen.</li>
                                <li>Keskellä näet pöydän tilanteen.</li>
                                <li>Oikealla näet oman kätesi.</li>
                                <li>Tapahtumaloki näyttää viimeisimmät siirrot.</li>
                            </ul>
                        </div>

                        <div className="text-sm text-slate-400">
                            Hetki vielä… peli käynnistyy automaattisesti.
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}