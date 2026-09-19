# Installa una selezione curata di skill nella cartella skills di Odysseus.
# Nota: Odysseus inietta l'INDICE di tutte le skill in ogni prompt (una riga
# per skill), quindi la selezione resta piccola di proposito.
$src  = 'd:\assistenteeee\skills-src\pm-claude-skills\skills'
$dest = 'd:\assistenteeee\odysseus\data\skills'

$selezione = @{
    'assistente-pc' = @('desktop-zero', 'file-access-preflight', 'git-troubleshooter', 'debugging-log-analyser', 'screenshot-teardown')
    'ricerca-web'   = @('fact-check-pass', 'source-triangulation', 'research-protocol', 'boolean-search-builder', 'multi-source-signal-synthesiser')
    'voce-persona'  = @('voice-agent-design', 'prompt-optimizer')
    'gaming'        = @('teach-the-game')
}

foreach ($categoria in $selezione.Keys) {
    foreach ($nome in $selezione[$categoria]) {
        $from = Join-Path $src "$nome\SKILL.md"
        if (-not (Test-Path $from)) { Write-Warning "manca: $nome"; continue }
        $dir = Join-Path $dest "$categoria\$nome"
        New-Item -ItemType Directory -Force $dir | Out-Null

        $testo = Get-Content $from -Raw
        # Il frontmatter Claude ha solo name/description: Odysseus vuole anche
        # category e status=published, altrimenti la skill resta invisibile.
        $testo = $testo -replace "(?s)^---\r?\n", "---`nstatus: published`ncategory: $categoria`nsource: community`n"
        Set-Content -Path (Join-Path $dir 'SKILL.md') -Value $testo -Encoding UTF8 -NoNewline
        Write-Host "installata: $categoria/$nome"
    }
}
