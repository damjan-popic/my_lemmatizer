# LORIS import report / Poročilo o uvozu LORIS

Source workbook: `Loris_novi vnosi_Final_1.2.xlsx`

Canonical source sheet: `Termini_EMZ`, rows 2–90.

## Summary / Povzetek

- Approved spreadsheet entries read / Prebranih potrjenih vnosov: **89**
- Existing paronym rules updated / Posodobljenih obstoječih pravil: **25**
- New paronym rules added / Dodanih novih pravil: **64**
- Final rule count / Končno število pravil: **1798**
- Category counts / Število po kategorijah: `{'nepravilni': 412, 'odsvetovani': 334, 'paronym': 286, 'prepovedani': 578, 'slogovni': 123, 'toponym': 65}`
- Trigger-type counts / Število po vrstah sprožilcev: `{'lemma': 1610, 'surface': 123, 'surface_name': 65}`

Duplicate policy: the import is an **upsert**. If a Termini_EMZ entry already had a `paronym` lemma trigger, the existing rule was refreshed instead of duplicated. If it did not exist, one new `paronym` rule was appended.

Politika podvajanja: uvoz deluje kot **upsert**. Če je vnos iz `Termini_EMZ` že imel `paronym` lemski sprožilec, je bilo obstoječe pravilo posodobljeno, ne podvojeno. Če vnosa še ni bilo, je bilo dodano novo pravilo `paronym`.

## Updated existing rules / Posodobljena obstoječa pravila

| Row | Izhodišče | Rule ID | Lemma triggers |
|---:|---|---|---|
| 9 | registrirati | `paronym_registrirati` | registrirati |
| 12 | tišina | `paronym_tišina` | tišina |
| 13 | predno | `paronym_predno` | predno |
| 15 | asikuracija | `paronym_asikuracija` | asikuracija |
| 16 | log | `paronym_log` | log |
| 17 | honorarij | `paronym_honorarij` | honorarij |
| 18 | nonprofit | `paronym_nonprofit` | nonprofit |
| 19 | slide | `paronym_slide` | slide |
| 20 | file | `paronym_file` | file |
| 21 | evidentirati | `paronym_evidentirati` | evidentirati |
| 24 | registrator | `paronym_registrator` | registrator |
| 27 | sponka | `paronym_sponka` | sponka |
| 28 | patent | `paronym_patent` | patent |
| 30 | soklopnik | `paronym_soklopnik` | soklopnik |
| 31 | soklopnica | `paronym_soklopnica` | soklopnica |
| 33 | konzulta | `paronym_konzulta` | konzulta |
| 35 | teza | `paronym_teza` | teza |
| 36 | agonističen | `paronym_agonističen` | agonističen |
| 37 | agonist | `paronym_agonist` | agonist |
| 38 | agonistka | `paronym_agonistka` | agonistka |
| 39 | upravitelj | `paronym_upravitelj` | upravitelj |
| 40 | upraviteljica | `paronym_upraviteljica` | upraviteljica |
| 46 | odstavka | `paronym_odstavka` | odstavka |
| 47 | protagonist | `paronym_protagonist` | protagonist |
| 62 | anticipirati | `paronym_anticipirati` | anticipirati |

## Added rules / Dodana pravila

| Row | Izhodišče | Rule ID | Lemma triggers |
|---:|---|---|---|
| 2 | zapreti luč | `paronym_zapreti_luč` | zapreti luč |
| 3 | odpreti luč | `paronym_odpreti_luč` | odpreti luč |
| 4 | na štiri roke | `paronym_na_štiri_roke` | na štiri roke |
| 5 | se pustiti it | `paronym_se_pustiti_it` | se pustiti it |
| 6 | privatist | `paronym_privatist` | privatist |
| 7 | privatiska | `paronym_privatiska` | privatiska |
| 8 | zmrzniti se | `paronym_zmrzniti_se` | zmrzniti se |
| 10 | stati (na) sredi med (dvema predmetoma) | `paronym_stati_na_sredi_med` | stati na sredi med<br>stati sredi med |
| 11 | plačevalka | `paronym_plačevalka` | plačevalka |
| 14 | aretacija | `paronym_aretacija` | aretacija |
| 22 | več | `paronym_več` | več |
| 23 | največ | `paronym_največ` | največ |
| 25 | za dopust | `paronym_za_dopust` | za dopust |
| 26 | intestiran papir | `paronym_intestiran_papir` | intestiran papir |
| 29 | hospitacija | `paronym_hospitacija` | hospitacija |
| 32 | abuzivno poslopje | `paronym_abuzivno_poslopje` | abuzivno poslopje |
| 34 | davčna koda | `paronym_davčna_koda` | davčna koda |
| 41 | reklamacija | `paronym_reklamacija` | reklamacija |
| 42 | oproščati se | `paronym_oproščati_se` | oproščati se |
| 43 | v vidiku | `paronym_v_vidiku` | v vidiku |
| 44 | v sklopu | `paronym_v_sklopu` | v sklopu |
| 45 | v okviru | `paronym_v_okviru` | v okviru |
| 48 | samomoriti (se) | `paronym_samomoriti_se` | samomoriti se<br>samomoriti |
| 49 | monitorirati | `paronym_monitorirati` | monitorirati |
| 50 | mimetizirati | `paronym_mimetizirati` | mimetizirati |
| 51 | recepirati | `paronym_recepirati` | recepirati |
| 52 | predvpisati | `paronym_predvpisati` | predvpisati |
| 53 | refinansirati | `paronym_refinansirati` | refinansirati |
| 54 | sponzorizirati | `paronym_sponzorizirati` | sponzorizirati |
| 55 | hipotizirati | `paronym_hipotizirati` | hipotizirati |
| 56 | sekvestrirati | `paronym_sekvestrirati` | sekvestrirati |
| 57 | getizirati | `paronym_getizirati` | getizirati |
| 58 | penalizirati | `paronym_penalizirati` | penalizirati |
| 59 | provati | `paronym_provati` | provati |
| 60 | iznesti | `paronym_iznesti` | iznesti |
| 61 | delegitimirati | `paronym_delegitimirati` | delegitimirati |
| 63 | redimenzionirati | `paronym_redimenzionirati` | redimenzionirati |
| 64 | ošemiti (se) | `paronym_ošemiti_se` | ošemiti se<br>ošemiti |
| 65 | publicizirati | `paronym_publicizirati` | publicizirati |
| 66 | delokalizirati | `paronym_delokalizirati` | delokalizirati |
| 67 | katalogirati | `paronym_katalogirati` | katalogirati |
| 68 | sofinansirati | `paronym_sofinansirati` | sofinansirati |
| 69 | kofinancirati | `paronym_kofinancirati` | kofinancirati |
| 70 | kolavdirati | `paronym_kolavdirati` | kolavdirati |
| 71 | samokandidirati | `paronym_samokandidirati` | samokandidirati |
| 72 | konfinirati | `paronym_konfinirati` | konfinirati |
| 73 | do sedaj | `paronym_do_sedaj` | do sedaj |
| 74 | kriminalnost | `paronym_kriminalnost` | kriminalnost |
| 75 | zgubljen | `paronym_zgubljen` | zgubljen |
| 76 | debutirati | `paronym_debutirati` | debutirati |
| 77 | bodyguard | `paronym_bodyguard` | bodyguard |
| 78 | browser | `paronym_browser` | browser |
| 79 | tolmačica | `paronym_tolmačica` | tolmačica |
| 80 | finansiranje | `paronym_finansiranje` | finansiranje |
| 81 | kvarantena | `paronym_kvarantena` | kvarantena |
| 82 | Mehikanec | `paronym_mehikanec` | Mehikanec |
| 83 | komemorirati | `paronym_komemorirati` | komemorirati |
| 84 | spoprijazniti | `paronym_spoprijazniti` | spoprijazniti |
| 85 | protiviti | `paronym_protiviti` | protiviti |
| 86 | inokulirati | `paronym_inokulirati` | inokulirati |
| 87 | rekreatorij | `paronym_rekreatorij` | rekreatorij |
| 88 | inkasirati | `paronym_inkasirati` | inkasirati |
| 89 | regularizirati | `paronym_regularizirati` | regularizirati |
| 90 | sensibilizirati | `paronym_sensibilizirati` | sensibilizirati |

## Notes / Opombe

- Spreadsheet slashes (`/`) and blank cells are treated as empty payload fields, so the frontend does not display meaningless slash-only values.
- Poševnice (`/`) in prazne celice so obravnavane kot prazna polja, zato frontend ne prikazuje polj, ki bi vsebovala samo `/`.
- Parenthetical shorthand in triggers is expanded where safe: `samomoriti (se)` → `samomoriti se`, `samomoriti`; `ošemiti (se)` → `ošemiti se`, `ošemiti`; `stati (na) sredi med (dvema predmetoma)` → `stati na sredi med`, `stati sredi med`.
- Oklepajni zapisi v sprožilcih so varno razširjeni: `samomoriti (se)` → `samomoriti se`, `samomoriti`; `ošemiti (se)` → `ošemiti se`, `ošemiti`; `stati (na) sredi med (dvema predmetoma)` → `stati na sredi med`, `stati sredi med`.
