let data, historyData, weekData, historyFailed=false, visible = 50;
const $ = id => document.getElementById(id);
const esc = value => String(value || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const copy = {
  en: {brand: 'SHORTAGE RADAR', languageLabel: 'Language', form_0:"Eye drops", form_1:"Ear drops", form_2:"Nasal spray", form_3:"Inhaled medicine", form_4:"Injection", form_5:"Infusion", form_6:"Cream", form_7:"Chewable tablet", form_8:"Tablet dissolved under the tongue", form_9:"Tablet", form_10:"Capsule", form_11:"Patch", form_12:"Oral solution", form_13:"Oral suspension", form_14:"Cream or ointment", form_15:"Gel", form_16:"Shampoo", form_17:"Suppository", form_18:"Enema", group_A:"Digestive and metabolic medicines", group_B:"Blood and circulation medicines", group_C:"Heart and blood pressure medicines", group_D:"Skin medicines", group_G:"Urinary and reproductive health medicines", group_H:"Hormone medicines", group_J:"Medicines for infections", group_L:"Cancer and immune system medicines", group_M:"Muscle and joint medicines", group_N:"Nervous system medicines", group_P:"Medicines for parasites", group_Q:"Veterinary medicines", group_R:"Breathing and allergy medicines", group_S:"Eye and ear medicines", group_V:"Other medicines", form_combined:"Medicine for injection or infusion", form_injectionPowder:"Powder for injection", form_infusionPowder:"Powder for infusion", form_oralSolutionPowder:"Powder for oral solution", form_oralSuspensionPowder:"Powder for oral suspension", group_eye:"Eye medicines", group_ear:"Ear medicines", chartAria:(a,b,n)=>`Saved snapshot counts from ${a} to ${b}, latest ${n}`, latest:d=>`LATEST SNAPSHOT ${d}`, country:"/ FINLAND", openData:"FIMEA OPEN DATA", heading:"Medicine shortages", headingPlace:"in Finland.", intro:"A clearer view of reported medicine shortages, updated from Fimea’s open data.", aboutTitle:"ABOUT THIS DATA", aboutText:"Includes current shortages and those expected to begin within two weeks. A listing does not tell you whether a medicine is available at your pharmacy.", overview:"Overview", statShortages:"LISTED SHORTAGES", statCurrent:"Current and upcoming, including veterinary products", statCompanies:"COMPANIES", statHolders:"Marketing authorisation holders", statArchive:"HISTORY FROM", dailySince:"Daily archive since 21 Nov 2026, with earlier captures from the Internet Archive.", listKicker:"THE LIST", searchLabel:"Search shortages", packageLevel:"FIMEA · PACKAGE LEVEL", pictureKicker:"THE PICTURE", pictureTitle:"Where shortages appear", pictureText:"Counts represent listed shortage records, not unique medicines.", byGroup:"By medicine group", byCompany:"By company", topTen:"top 10", historyKicker:"OVER TIME", historyTitle:"A history, starting here.", historyText:"Snapshots are saved when the source changes. Gaps do not prove daily observations, and removal from the list is not proof of actual supply.", chartLabel:"Shortage counts by saved snapshot", delayKicker:"ESTIMATED END DATES", delayTitle:"Did shortages leave the list by the estimated date?", noticeTitle:"Not medical advice.", footerAgency:"Finnish Medicines Agency Fimea", footerTransform:"Data was selected, joined and transformed.", footerNote:"Source times show when the files were last modified; the publisher does not provide release times.", sourceLink:"Source and licence ↗", pageTitle:"Shortage Radar — Finland", description:"A clearer view of reported medicine shortages in Finland.", loading:"Loading shortages…", loadingData:"Loading data…", loadError:"Unable to load data", listError:"Data could not be loaded. Please try again later.", startUnknown:"Start date unknown", startUnknownSentence:"Start date not known.", chartEmpty:"A chart will appear when at least two snapshots are available.", unknownCompany:"Unknown", delayEmpty:"Needs more weeks of data.", firstEstimate:"first estimate", removedBy:"removed by", shortageFile:"Fimea shortage file", register:"Basic register", helpTitle:'What is a shortage?', help:'The company has told Fimea it cannot deliver this package for a while. Your pharmacy may still have some. Ask your pharmacy what is available.', title:'Reported shortages', hint:'Search by medicine, active substance, ATC, company or VNR.', placeholder:'e.g. Burana or ibuprofen', count:n=>`${numberText(n)} ${n === 1 ? 'record' : 'records'}`, more:'Show more', empty:'Not on the list. That does not guarantee your pharmacy has it. Try the active substance (for example paracetamol) or ask your pharmacy.', out:'Shortage now', soon:'Starts soon', since:'Shortage reported from', starts:'Expected to become unavailable on', expected:'Expected back around', estimate:"the company’s estimate", unknown:'Return date not known.', late:'Later than estimated', days:n=>`${numberText(n)} ${n === 1 ? 'day' : 'days'}`, details:'Details', strength:'Strength', substance:'Active substance', company:'Company', reported:'Report date', unavailable:'Name unavailable', group:'Medicine group', noGroup:'Group not listed', form:'Original form', otherForm:'Other form'},
  fi: {brand: 'SAATAVUUSTUTKA', languageLabel: 'Kieli', form_0:"Silmätipat", form_1:"Korvatipat", form_2:"Nenäsumute", form_3:"Inhalaatiolääke", form_4:"Injektioneste", form_5:"Infuusioneste", form_6:"Emulsiovoide", form_7:"Purutabletti", form_8:"Kielen alle liukeneva tabletti", form_9:"Tabletti", form_10:"Kapseli", form_11:"Laastari", form_12:"Oraaliliuos", form_13:"Oraalisuspensio", form_14:"Voide", form_15:"Geeli", form_16:"Sampoo", form_17:"Peräpuikko", form_18:"Peräruiske", group_A:"Ruoansulatuksen ja aineenvaihdunnan lääkkeet", group_B:"Veren ja verenkierron lääkkeet", group_C:"Sydän- ja verenpainelääkkeet", group_D:"Iholääkkeet", group_G:"Virtsateiden ja lisääntymisterveyden lääkkeet", group_H:"Hormonilääkkeet", group_J:"Infektiolääkkeet", group_L:"Syöpä- ja immuunijärjestelmän lääkkeet", group_M:"Lihas- ja nivelsairauksien lääkkeet", group_N:"Hermoston lääkkeet", group_P:"Loislääkkeet", group_Q:"Eläinlääkkeet", group_R:"Hengitystie- ja allergialääkkeet", group_S:"Silmä- ja korvalääkkeet", group_V:"Muut lääkkeet", form_combined:"Injektio- tai infuusiolääke", form_injectionPowder:"Injektiokuiva-aine", form_infusionPowder:"Infuusiokuiva-aine", form_oralSolutionPowder:"Jauhe oraaliliuosta varten", form_oralSuspensionPowder:"Jauhe oraalisuspensiota varten", group_eye:"Silmälääkkeet", group_ear:"Korvalääkkeet", chartAria:(a,b,n)=>`Tallennettujen tilannekuvien ilmoitusmäärät ${a}–${b}, viimeisin ${n}`, latest:d=>`VIIMEISIN TILANNEKUVA ${d}`, country:"/ SUOMI", openData:"FIMEAN AVOIN DATA", heading:"Lääkkeiden", headingPlace:"saatavuushäiriöt Suomessa.", intro:"Selkeä näkymä ilmoitettuihin lääkkeiden saatavuushäiriöihin Fimean avoimen datan perusteella.", aboutTitle:"TIETOA AINEISTOSTA", aboutText:"Mukana ovat nykyiset häiriöt ja kahden viikon kuluessa alkaviksi arvioidut häiriöt. Ilmoitus ei kerro, onko lääkettä saatavilla omassa apteekissasi.", overview:"Yhteenveto", statShortages:"ILMOITETUT HÄIRIÖT", statCurrent:"Nykyiset ja tulevat, myös eläinlääkkeet", statCompanies:"YRITYKSET", statHolders:"Myyntiluvan haltijat", statArchive:"HISTORIA ALKAEN", dailySince:"Päivittäinen arkisto alkaen 21.11.2026, aiemmat tallenteet Internet Archivesta.", listKicker:"LISTA", searchLabel:"Hae saatavuushäiriöitä", packageLevel:"FIMEA · PAKKAUSTASO", pictureKicker:"YLEISKUVA", pictureTitle:"Missä häiriöitä esiintyy", pictureText:"Luvut kuvaavat ilmoituksia, eivät yksittäisten lääkkeiden määrää.", byGroup:"Lääkeryhmittäin", byCompany:"Yrityksittäin", topTen:"10 suurinta", historyKicker:"AIKANA", historyTitle:"Historia alkaa tästä.", historyText:"Tilannekuva tallennetaan, kun lähdeaineisto muuttuu. Aukot eivät osoita päivittäisiä havaintoja, eikä listalta poistuminen todista, että lääkettä on saatavilla.", chartLabel:"Ilmoitusten määrä tallennetuissa tilannekuvissa", delayKicker:"ARVIOIDUT PÄÄTTYMISPÄIVÄT", delayTitle:"Poistuivatko häiriöt listalta arvioituun päivään mennessä?", noticeTitle:"Tämä ei ole lääketieteellinen neuvo.", footerAgency:"Lääkealan turvallisuus- ja kehittämiskeskus Fimea", footerTransform:"Aineistoa on valikoitu, yhdistetty ja muokattu.", footerNote:"Lähteiden ajat kertovat, milloin tiedostoja on viimeksi muutettu; julkaisija ei ilmoita julkaisuaikoja.", sourceLink:"Lähde ja lisenssi ↗", pageTitle:"Saatavuustutka — Suomi", description:"Selkeä näkymä Suomessa ilmoitettuihin lääkkeiden saatavuushäiriöihin.", loading:"Ladataan saatavuushäiriöitä…", loadingData:"Ladataan tietoja…", loadError:"Tietojen lataaminen epäonnistui", listError:"Tietoja ei voitu ladata. Yritä myöhemmin uudelleen.", startUnknown:"Alkamispäivä ei tiedossa", startUnknownSentence:"Alkamispäivä ei ole tiedossa.", chartEmpty:"Kaavio tulee näkyviin, kun vähintään kaksi tilannekuvaa on tallennettu.", unknownCompany:"Ei tiedossa", delayEmpty:"Tietoja tarvitaan useammalta viikolta.", firstEstimate:"ensimmäinen arvio", removedBy:"poistunut listalta", shortageFile:"Fimean saatavuushäiriötiedosto", register:"Perusrekisteri", helpTitle:'Mitä saatavuushäiriö tarkoittaa?', help:'Yritys on ilmoittanut Fimealle, ettei se voi toimittaa tätä pakkausta vähään aikaan. Apteekissa sitä voi silti olla. Kysy apteekista, mitä on saatavilla.', title:'Ilmoitetut saatavuushäiriöt', hint:'Hae lääkkeen tai vaikuttavan aineen nimellä, ATC-koodilla, yrityksellä tai VNR-numerolla.', placeholder:'esim. Burana tai ibuprofeeni', count:n=>`${numberText(n)} ${n === 1 ? 'ilmoitus' : 'ilmoitusta'}`, more:'Näytä lisää', empty:'Ei listalla. Se ei takaa, että apteekissasi on lääkettä. Kokeile vaikuttavaa ainetta (esimerkiksi parasetamoli) tai kysy apteekista.', out:'Saatavuushäiriö nyt', soon:'Alkaa pian', since:'Saatavuushäiriö ilmoitettu alkavaksi', starts:'Saatavuushäiriön arvioidaan alkavan', expected:'Arvioidaan olevan taas saatavilla noin', estimate:'yrityksen arvio', unknown:'Saatavuuden palautumisen ajankohta ei ole tiedossa.', late:'Arvio on ylittynyt', days:n=>`${numberText(n)} ${n === 1 ? 'päivä' : 'päivää'}`, details:'Lisätiedot', strength:'Vahvuus', substance:'Vaikuttava aine', company:'Yritys', reported:'Ilmoituspäivä', unavailable:'Nimi ei tiedossa', group:'Lääkeryhmä', noGroup:'Lääkeryhmää ei ole ilmoitettu', form:'Alkuperäinen lääkemuoto', otherForm:'Muu lääkemuoto'}
};
Object.assign(copy.en, {
  archiveCredit: 'Earlier captures:',
  delayBias: ' Shortages still on the list are not counted, so the share past the estimate is likely higher.',
  activePast: (n,date,gap) => ` On ${date}, ${n} shortages were still listed past their first estimated end date and had first been seen within ${gap} days of the preceding capture.`,
  savedLegend: '● saved by this project', importedLegend: '○ imported from the Internet Archive',
  capturePoint: (date, count, source) => `${date}: ${count} records (${source})`, savedSource: 'saved by this project', importedSource: 'imported from the Internet Archive',
  noCaptures: n => `no captures · ${n} days`, gapBefore: (n, date) => `${n} days before ${date}`,
  chartSummary: (a,b,n,gaps) => `Capture counts from ${a} to ${b}; latest ${n}.${gaps ? ` Gaps without captures: ${gaps} days.` : ''}`,
  historySummary: (total,date,imported,own,gaps,first) => `${total} captures since ${date}: ${imported} imported from the Internet Archive and ${own} saved by this project.${gaps ? ` Longer gaps without captures: ${gaps}.` : ''} ${first} records were already listed at the first capture, so their start is unknown. The chart does not interpolate across gaps.`,
  rssSummary: items => `Earlier counts from archived copies of Fimea's RSS feed: ${items}. These items have no VNR and cannot be compared with package counts above.`, rssItem: (date,n) => `${date}: ${n} items`,
  delaySample: (n,gap) => `${n} ${n === '1' ? 'shortage' : 'shortages'} entered and left the list within the covered period, with captures at most ${gap} days apart at both ends. Left the list means the record was absent from a later capture; it does not prove the medicine is back.`,
  delayResult: (past,notPast,unknown,min,max) => ` Of these, ${past} were still listed after the first estimated end date, ${notPast} had left by then, and ${unknown} cannot be determined between captures. The share listed past the estimate is ${min}–${max}.`,
  delayMedian: range => ` For those still listed past the estimate, the median overrun was ${range} (lower and upper bounds).`, delaySmall: n => ` This is fewer than ${n}, too few for shares or medians.`,
  delayExcluded: (first,noEstimate,start,end,changed) => ` Excluded: ${first} already listed at the first capture, ${noEstimate} without an estimate, ${start} first seen after a long gap, ${end} removed across a long gap, and ${changed} whose package remained listed under a changed record.`,
  delayExamples: 'Longest observed overruns', lastListed: 'last listed', goneBy: 'gone by', dayRange: (a,b) => `${a === b ? a : `${a}–${b}`} days`
});
Object.assign(copy.fi, {
  archiveCredit: 'Aiemmat tallenteet:',
  delayBias: ' Edelleen listalla olevia saatavuushäiriöitä ei lasketa mukaan, joten arvion ylittäneiden todellinen osuus on todennäköisesti suurempi.',
  activePast: (n,date,gap) => ` Tilannekuvassa ${date} oli edelleen listalla ${n} saatavuushäiriötä ensimmäisen arvioidun päättymispäivän jälkeen. Ne oli havaittu ensimmäisen kerran enintään ${gap} päivää edellisen tilannekuvan jälkeen.`,
  savedLegend: '● tämän hankkeen tallentama', importedLegend: '○ Internet Archivesta tuotu',
  capturePoint: (date, count, source) => `${date}: ${count} ilmoitusta (${source})`, savedSource: 'tämän hankkeen tallentama', importedSource: 'Internet Archivesta tuotu',
  noCaptures: n => `ei tilannekuvia · ${n} päivää`, gapBefore: (n,date) => `${n} päivää ennen ${date}`,
  chartSummary: (a,b,n,gaps) => `Tilannekuvien ilmoitusmäärät ${a}–${b}, viimeisin ${n}.${gaps ? ` Aukot ilman tilannekuvia: ${gaps} päivää.` : ''}`,
  historySummary: (total,date,imported,own,gaps,first) => `${total} tilannekuvaa alkaen ${date}: ${imported} tuotu Internet Archivesta ja ${own} tämän hankkeen tallentamaa.${gaps ? ` Pidemmät aukot ilman tilannekuvia: ${gaps}.` : ''} Ensimmäisessä tilannekuvassa oli jo ${first} ilmoitusta, joiden alkamisajankohta ei ole tiedossa. Kaaviossa aukkoja ei täytetä arvioilla.`,
  rssSummary: items => `Fimean RSS-syötteen arkistoiduista kopioista poimittuja aiempia lukumääriä: ${items}. Ilmoituksissa ei ole VNR-numeroa, joten niitä ei voi verrata yllä oleviin pakkausmääriin.`, rssItem: (date,n) => `${date}: ${n} ilmoitusta`,
  delaySample: (n,gap) => `Tarkastelussa on ${n} saatavuushäiriötä, jotka tulivat listalle ja poistuivat siltä tarkastelujaksolla. Tilannekuvien väli oli sekä alussa että lopussa enintään ${gap} päivää. Listalta poistuminen tarkoittaa, ettei ilmoitus näkynyt myöhemmässä tilannekuvassa; se ei todista, että lääkettä on taas saatavilla.`,
  delayResult: (past,notPast,unknown,min,max) => ` Näistä ${past} oli listalla vielä ensimmäisen arvioidun päättymispäivän jälkeen ja ${notPast} oli poistunut siihen mennessä. ${unknown} ilmoituksen osalta asiaa ei voi päätellä tilannekuvista. Arvion jälkeen listalla olleiden osuus on ${min}–${max}.`,
  delayMedian: range => ` Arvion jälkeen listalla olleiden viiveen mediaani oli ${range} (ala- ja yläraja).`, delaySmall: n => ` Määrä on alle ${n}, joten osuuksia tai mediaaneja ei esitetä.`,
  delayExcluded: (first,noEstimate,start,end,changed) => ` Tarkastelusta jätettiin pois ${first} jo ensimmäisessä tilannekuvassa ollutta ilmoitusta, ${noEstimate} ilman arviota, ${start} pitkän aukon jälkeen havaittua, ${end} pitkän aukon aikana poistunutta ja ${changed}, joiden pakkaus jäi listalle muuttuneella ilmoituksella.`,
  delayExamples: 'Pisimmät havaitut viiveet', lastListed: 'viimeksi listalla', goneBy: 'poistunut viimeistään', dayRange: (a,b) => `${a === b ? a : `${a}–${b}`} päivää`
});
Object.assign(copy.en, {skip:'Skip to shortages', sortLabel:'Sort by', sortNewest:'Newest', sortName:'Name', sortLongest:'Longest running', longestTitle:'Longest current shortages', longestNote:'Time since the reported start date.', veterinary:'Veterinary', download:'Download the data:', checked:d=>`Checked ${d}`, stale:'Data was last checked more than 3 days ago.'});
Object.assign(copy.fi, {skip:'Siirry saatavuushäiriöihin', sortLabel:'Järjestä', sortNewest:'Uusimmat', sortName:'Nimi', sortLongest:'Pisimpään jatkuneet', longestTitle:'Pisimpään jatkuneet saatavuushäiriöt', longestNote:'Aika ilmoitetusta alkamispäivästä.', veterinary:'Eläinlääke', download:'Lataa aineisto:', checked:d=>`Tarkistettu ${d}`, stale:'Aineisto on tarkistettu yli 3 päivää sitten.'});
Object.assign(copy.en, {buildOnly:'Build time; the last source check is unknown.', staleBuild:'The build is more than 3 days old.'});
Object.assign(copy.fi, {buildOnly:'Koostamisaika; viimeisin lähteen tarkistus ei ole tiedossa.', staleBuild:'Koostamisesta on yli 3 päivää.'});
Object.assign(copy.en, {form:'Form on the package (Finnish)', latest:d=>`Latest snapshot ${d}`, updated:d=>`Updated ${d}`, sourceError:'Fimea open data', historyError:'History could not be loaded.', delayHeadline:(past,total,unknown,a,b)=>`${past} of ${total} observed shortages stayed listed past the estimate; for ${unknown} we cannot tell yet. The share listed past the estimate is ${a}–${b}.`, delayBy:'Left by the estimate', delayPast:'Listed after the estimate', delayUncertain:'Timing uncertain', delayActive:n=>`${n} other shortages were still listed past the estimate.`, delayMethod:(n,g)=>`Among ${n} shortages that entered and left the list, captures were at most ${g} days apart at both ends. Removal from the list does not prove supply returned. The uncertain cases set the range; ongoing shortages are not included in it.`});
Object.assign(copy.fi, {latest:d=>`Viimeisin tilannekuva ${d}`, updated:d=>`Päivitetty ${d}`, sourceError:'Fimean avoin data', historyError:'Historiaa ei voitu ladata.', delayHeadline:(past,total,unknown,a,b)=>`${total} havaitusta saatavuushäiriöstä ${past} pysyi listalla arvion jälkeen; ${unknown} osalta ei vielä voi sanoa. Arvion jälkeen listalla olleiden osuus on ${a}–${b}.`, delayBy:'Poistui arvioon mennessä', delayPast:'Listalla arvion jälkeen', delayUncertain:'Ajankohta epävarma', delayActive:n=>`${n} muuta saatavuushäiriötä oli edelleen listalla arvion jälkeen.`, delayMethod:(n,g)=>`Mukana on ${n} listalle tullutta ja siltä poistunutta häiriötä, joiden molemmissa päissä tilannekuvien väli oli enintään ${g} päivää. Listalta poistuminen ei todista saatavuuden palautumista. Epävarmat tapaukset määrittävät vaihteluvälin; jatkuvat häiriöt eivät sisälly siihen.`});
copy.en.delayMethod=(n,g)=>`Among ${n} shortages that entered and left the list, captures were at most ${g} days apart at both ends. The first observed estimate may already have been revised. Removal does not prove supply returned; uncertain cases set the range and ongoing shortages are excluded.`;
copy.fi.delayMethod=(n,g)=>`Mukana on ${n} listalle tullutta ja siltä poistunutta häiriötä, joiden molemmissa päissä tilannekuvien väli oli enintään ${g} päivää. Ensimmäistä havaittua arviota on voitu muuttaa jo aiemmin. Poistuminen ei todista saatavuuden palautumista; epävarmat tapaukset määrittävät vaihteluvälin ja jatkuvat häiriöt eivät sisälly siihen.`;
Object.assign(copy.en, {
  aboutLink:'About the data', aboutShort:'About', moreInfo:c=>`For more information, ask your pharmacy or the company${c ? ` (${c})` : ''}.`, moreInfoLink:'Fimea’s shortage search', moreInfoUrl:'https://fimea.fi/en/databases_and_registers/shortages',
  weekTitle:'This week', weekWindow:(from,days)=>`Compared with the capture of ${from}, ${days} days earlier. A changed record for a package that was already listed is not counted.`,
  weekNew:'NEW ON THE LIST', weekNewNote:from=>`New records listed since ${from}, including any that left again.`,
  weekLeft:'LEFT THE LIST', weekLeftNote:from=>`Records that left the list since ${from}, including any that arrived in the same period. This does not show that supply returned.`,
  weekTotal:'LISTED NOW', weekTotalNote:(now,n,from)=>`${now} now · ${n} on ${from}`, feedLink:'Follow changes (feed)',
  howTitle:'How we count', howText:(n,total,gap,skipped)=>`Counted: ${n} of the ${total} records that have left the list. These were first seen and last seen within ${gap} days of a neighbouring capture and had an estimated end date.${skipped ? ` Not counted: ${skipped}.` : ''}`,
  howFirst:n=>`${n} already listed at the first capture`, howNoEstimate:n=>`${n} without an estimated end date`, howStart:n=>`${n} first seen after a long gap`, howEnd:n=>`${n} removed across a long gap`, howChanged:n=>`${n} whose package stayed listed under a changed record`,
  aboutKicker:'ABOUT', aboutPageTitle:'About this site', aboutSourceTitle:'Where the data comes from', aboutSource:'The list comes from Fimea, the Finnish Medicines Agency, which publishes it as open data. The archive checks Fimea’s file every day. Daily archive since 21 Nov 2026, with earlier captures from the Internet Archive.',
  aboutRecordTitle:'What one record is', aboutRecord:'One record is one medicine package. The company that holds the marketing authorisation reported it to Fimea. A medicine can have several packages, so the counts are records, not medicines.',
  aboutLimitsTitle:'What the data cannot tell you', aboutLimits:'A record that leaves the list is not proof that the medicine is back in supply. The history from before this site started saving the file comes from the Internet Archive and has gaps. Dates in the history are capture dates, not exact event dates.',
  aboutCiteTitle:'Licence and how to cite', aboutCite:'Fimea’s data is licensed under CC BY 4.0. This site selects, joins and transforms it.',
  aboutAdvice:'This site does not tell you what to take or whether a medicine is available. Ask a pharmacist or doctor about your medicines.', aboutGithub:'Code, data files and method on GitHub ↗', citeTitle:'Cite this site', citation:(data,today)=>`Alejandro Renalias, Shortage Radar, https://alejandrorenalias.github.io/shortage-radar/ (data dated ${data}, accessed ${today}); data from the Finnish Medicines Agency Fimea, CC BY 4.0, selected, joined and transformed; earlier captures from the Internet Archive.`, copyCite:'Copy citation', copied:'Copied', reportProblem:'Report a data problem ↗', askPharmacy:'Ask your pharmacy', jump:'Show results ↓'
});
Object.assign(copy.fi, {
  aboutLink:'Tietoa aineistosta', aboutShort:'Tietoa', moreInfo:c=>`Lisätietoja saat apteekista tai yritykseltä${c ? ` (${c})` : ''}.`, moreInfoLink:'Fimean saatavuushäiriöhaku', moreInfoUrl:'https://fimea.fi/laakehaut_ja_luettelot/saatavuushairio-uusi',
  weekTitle:'Tällä viikolla', weekWindow:(from,days)=>`Vertailukohtana on ${from} tallennettu tilannekuva, ${days} päivää aiemmin. Jo listalla olleen pakkauksen muuttunutta ilmoitusta ei lasketa.`,
  weekNew:'UUDET LISTALLA', weekNewNote:from=>`Listalle ${from} jälkeen tulleet ilmoitukset, myös ne, jotka ehtivät poistua uudelleen.`,
  weekLeft:'POISTUNEET LISTALTA', weekLeftNote:from=>`Listalta ${from} jälkeen poistuneet ilmoitukset, myös samalla jaksolla listalle tulleet. Tämä ei osoita, että saatavuus on palautunut.`,
  weekTotal:'LISTALLA NYT', weekTotalNote:(now,n,from)=>`${now} nyt · ${n} päivänä ${from}`, feedLink:'Seuraa muutoksia (syöte)',
  howTitle:'Näin laskemme', howText:(n,total,gap,skipped)=>`Mukana on ${n} listalta poistuneesta ${total} ilmoituksesta. Ne havaittiin ensimmäisen ja viimeisen kerran enintään ${gap} päivän päässä viereisestä tilannekuvasta, ja niillä oli arvioitu päättymispäivä.${skipped ? ` Pois jätettiin: ${skipped}.` : ''}`,
  howFirst:n=>`${n} jo ensimmäisessä tilannekuvassa ollutta`, howNoEstimate:n=>`${n} ilman arvioitua päättymispäivää`, howStart:n=>`${n} pitkän aukon jälkeen havaittua`, howEnd:n=>`${n} pitkän aukon aikana poistunutta`, howChanged:n=>`${n} muuttuneella ilmoituksella listalle jäänyttä pakkausta`,
  aboutKicker:'TIETOA', aboutPageTitle:'Tietoa tästä sivustosta', aboutSourceTitle:'Mistä tiedot tulevat', aboutSource:'Lista tulee Fimealta, eli Lääkealan turvallisuus- ja kehittämiskeskukselta, joka julkaisee sen avoimena datana. Arkisto tarkistaa Fimean tiedoston joka päivä. Päivittäinen arkisto alkaen 21.11.2026, aiemmat tallenteet Internet Archivesta.',
  aboutRecordTitle:'Mitä yksi ilmoitus on', aboutRecord:'Yksi ilmoitus koskee yhtä lääkepakkausta. Myyntiluvan haltija on ilmoittanut sen Fimealle. Lääkkeellä voi olla useita pakkauksia, joten luvut ovat ilmoituksia, eivät lääkkeitä.',
  aboutLimitsTitle:'Mitä aineisto ei kerro', aboutLimits:'Listalta poistuminen ei todista, että lääke on taas saatavilla. Historia ajalta ennen tiedoston tallentamista on peräisin Internet Archivesta, ja siinä on aukkoja. Historian päivät ovat tilannekuvien päiviä, eivät tarkkoja tapahtumapäiviä.',
  aboutCiteTitle:'Lisenssi ja lähdeviite', aboutCite:'Fimean aineisto on lisensoitu CC BY 4.0 -lisenssillä. Tämä sivusto valikoi, yhdistää ja muokkaa sitä.',
  aboutAdvice:'Tämä sivusto ei kerro, mitä sinun pitäisi ottaa tai onko lääke saatavilla. Kysy lääkkeistäsi apteekista tai lääkäriltä.', aboutGithub:'Koodi, aineistot ja menetelmä GitHubissa ↗', citeTitle:'Lähdeviite', citation:(data,today)=>`Alejandro Renalias, Saatavuustutka, https://alejandrorenalias.github.io/shortage-radar/ (aineisto ${data}, viitattu ${today}); aineisto: Lääkealan turvallisuus- ja kehittämiskeskus Fimea, CC BY 4.0, valikoitu, yhdistetty ja muokattu; aiemmat tallenteet Internet Archivesta.`, copyCite:'Kopioi lähdeviite', copied:'Kopioitu', reportProblem:'Ilmoita aineiston virheestä ↗', askPharmacy:'Kysy apteekista', jump:'Näytä tulokset ↓'
});
const queryFromUrl = search => { try { return (new URLSearchParams(search).get('q') || '').trim().slice(0,100); } catch (_) { return ''; } };
const aliases = {parasetamoli:'paracetamol', ibuprofeeni:'ibuprofen', insuliini:'insulin', asetyylisalisyylihappo:'acetylsalicylic acid', amoksisilliini:'amoxicillin', atsitromysiini:'azithromycin', doksisykliini:'doxycycline', metformiini:'metformin', atorvastatiini:'atorvastatin', simvastatiini:'simvastatin', rosuvastatiini:'rosuvastatin', amlodipiini:'amlodipine', bisoprololi:'bisoprolol', metoprololi:'metoprolol', propranololi:'propranolol', losartaani:'losartan', kandesartaani:'candesartan', enalapriili:'enalapril', ramipriili:'ramipril', furosemidi:'furosemide', spironolaktoni:'spironolactone', varfariini:'warfarin', apiksabaani:'apixaban', rivaroksabaani:'rivaroxaban', klopidogreeli:'clopidogrel', omepratsoli:'omeprazole', pantopratsoli:'pantoprazole', esomepratsoli:'esomeprazole', levotyroksiini:'levothyroxine', prednisoloni:'prednisolone', hydrokortisoni:'hydrocortisone', deksametasoni:'dexamethasone', salbutamoli:'salbutamol', budesonidi:'budesonide', formoteroli:'formoterol', setiritsiini:'cetirizine', loratadiini:'loratadine', desloratadiini:'desloratadine', sertraliini:'sertraline', sitalopraami:'citalopram', essitalopraami:'escitalopram', fluoksetiini:'fluoxetine', venlafaksiini:'venlafaxine', duloksetiini:'duloxetine', mirtatsapiini:'mirtazapine', amitriptyliini:'amitriptyline', diatsepaami:'diazepam', oksatsepaami:'oxazepam', tematsepaami:'temazepam', tsolpideemi:'zolpidem', melatoniini:'melatonin', tramadoli:'tramadol', kodeiini:'codeine', morfiini:'morphine', oksikodoni:'oxycodone', gabapentiini:'gabapentin', pregabaliini:'pregabalin', levetirasetaami:'levetiracetam', lamotrigiini:'lamotrigine', karbamatsepiini:'carbamazepine', metotreksaatti:'methotrexate', allopurinoli:'allopurinol', diklofenaakki:'diclofenac', naprokseeni:'naproxen', ketoprofeeni:'ketoprofen', finasteridi:'finasteride', tamsulosiini:'tamsulosin', metronidatsoli:'metronidazole', flukonatsoli:'fluconazole', nitrofurantoiini:'nitrofurantoin', siprofloksasiini:'ciprofloxacin', klindamysiini:'clindamycin', fenoksimetyylipenisilliini:'phenoxymethylpenicillin', asikloviiri:'aciclovir', valasikloviiri:'valaciclovir', ondansetroni:'ondansetron', metoklopramidi:'metoclopramide'};
const fold = s => String(s || '').toLocaleLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
// Strengths are stored with decimal points; Finnish readers write and search "2,5".
// Strengths are raw register wording. Finnish readers get a decimal comma; English readers get common Finnish unit words translated. A number and its unit never break apart.
const strengthWords = {tuntia:'hours', tunti:'hour', annosta:'dose', annos:'dose', mikrog:'microg', 'yksikköä':'units', 'yksikkö':'unit', vuorokautta:'day', vuorokausi:'day'};
function strengthText(e) {
  let text=String(e.strength || '').replace(/\s+/g,' ').trim();
  text = language === 'fi' ? text.replace(/(\d)\.(?=\d)/g,'$1,') : text.replace(/(?<=\d )h(?![\p{L}])/gu,'hours').replace(/(?<![\p{L}])(tuntia|tunti|annosta|annos|mikrog|yksikköä|yksikkö|vuorokautta|vuorokausi)(?![\p{L}])/giu, w => strengthWords[w.toLocaleLowerCase()]);
  return text.replace(/(\d) (?=[\p{L}%µ])/gu,'$1\u00a0');
}
const plainText = s => String(s || '').replace(/\u00a0/g,' ').toLocaleLowerCase();
// The strength to show next to a name or pack: nothing when the pack label already starts with it ("10 mg + 2 ml").
function strengthShown(e) {
  const strength=strengthText(e), pack=plainText(packText(e)), own=plainText(strength);
  return !strength || (pack.startsWith(own) && !/^[\p{L}\d.,]/u.test(pack.slice(own.length))) ? '' : strength;
}
function nameWithStrength(e) { const name=e.name || '', strength=strengthShown(e); return !strength || plainText(name).includes(plainText(strength)) ? name : `${name} ${strength}`.trim(); }
const foldNumbers = s => s.replace(/(\d),(?=\d)/g,'$1.');
const NUMBER = /^\d+(?:\.\d*)?$/;
function searchMatches(e, query) {
  const q=foldNumbers(fold(query.trim()));
  const termsFor=word=>[word, ...Object.entries(aliases).filter(([fi])=>{const key=fold(fi); return word.length>=3 && !word.includes(' ') && (key.startsWith(word) || word.startsWith(key.slice(0,-1)));}).map(([,en])=>fold(en))];
  const fields=[e.name,e.strength,e.substances,e.atc,e.Company,e.NordicArticleNumber].map(x=>foldNumbers(fold(x)));
  if (fields.some(x=>termsFor(q).some(term=>x.includes(term)))) return true;
  // Several words match across fields, so "apixaban 5 mg" finds the 5 mg packs of Apixaban Sandoz.
  const words=q.replace(/(^|\s)(\d+(?:\.\d+)?)(mg|g|ml|mikrog|mcg|iu|%)(?=\s|$)/g,'$1$2 $3').split(/\s+/).filter(Boolean).map(word=>word.replace(/^(\d+),$/,'$1.'));
  if (words.length < 2) return false;
  const text=fields.join('\n');
  // A number matches whole numbers only, so "5" does not match "2.5" or "50"; a trailing point allows "2," while typing.
  return words.every(word=>NUMBER.test(word) ? new RegExp(String.raw`(?<![\d.])` + word.replace('.', String.raw`\.`) + (word.endsWith('.') ? '' : String.raw`(?!\d|\.\d)`)).test(text) : termsFor(word).some(term=>text.includes(term)));
}
let language = 'en';
try { const saved = localStorage.getItem('language'); language = ['en','fi'].includes(saved) ? saved : ((navigator.language || '').toLowerCase().startsWith('fi') ? 'fi' : 'en'); } catch (_) { language = (typeof navigator !== 'undefined' && (navigator.language || '').toLowerCase().startsWith('fi')) ? 'fi' : 'en'; }
const numberText = n => new Intl.NumberFormat(language === 'fi' ? 'fi-FI' : 'en-GB').format(n);
// Ordered so specific forms are matched before general ingredients of their names.
const forms = ["silmätipat", "korvatipat", "nenäsumute", "inhalaatio", "injektio", "infuusio", "emulsiovoide", "purutabletti", "resoribletti", "tabletti", "kapseli", "laastari", "oraaliliuos", "oraalisuspensio", "voide", "geeli", "shampoo", "peräpuikko", "peräruisk"];
function parsedDate(s) { if (!/^\d{4}-\d{2}-\d{2}$/.test(s || '')) return null; const d = new Date(`${s}T00:00:00Z`); return Number.isNaN(d.valueOf()) ? null : d; }
const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function formatDate(d) { return language === 'fi' ? `${d.getUTCDate()}.${d.getUTCMonth()+1}.${d.getUTCFullYear()}` : `${d.getUTCDate()} ${months[d.getUTCMonth()]} ${d.getUTCFullYear()}`; }
function dateText(s) { const d=parsedDate(s); return d ? formatDate(d) : '—'; }
function timestampText(s) { const d=new Date(s); if (Number.isNaN(d.valueOf())) return ''; const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Helsinki',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(d); const get=k=>parts.find(p=>p.type===k).value; const local=new Date(Date.UTC(+get('year'),+get('month')-1,+get('day'))); return language==='fi' ? `${formatDate(local)} klo ${+get('hour')}.${get('minute')} Suomen aikaa` : `${formatDate(local)}, ${get('hour')}:${get('minute')} Helsinki time`; }
function todayUTC() { const parts = new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Helsinki',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()); const get = type => parts.find(p=>p.type===type).value; return Date.UTC(+get('year'),+get('month')-1,+get('day')); }
function freshnessInfo(d, now = Date.now(), today = todayUTC()) {
  const t=copy[language], checked=parsedDate(d.last_checked);
  if (checked) return {text:t.checked(dateText(d.last_checked)), stale:today-checked.valueOf()>3*86400000, warning:t.stale};
  const built=d.generated_at && new Date(d.generated_at);
  if (built && !Number.isNaN(built.valueOf())) return {text:`${t.checked(timestampText(d.generated_at))} · ${t.buildOnly}`, stale:now-built.valueOf()>3*86400000, warning:t.staleBuild};
  return {text:'', stale:false, warning:''};
}
function formText(form) {
  if (!form) return '';
  const value = form.toLocaleLowerCase();
  if (value.includes('injektio') && value.includes('infuusio')) return copy[language].form_combined;
  if ((value.includes('jauhe') || value.includes('kuiva-aine')) && value.includes('injektio')) return copy[language].form_injectionPowder;
  if ((value.includes('jauhe') || value.includes('kuiva-aine')) && value.includes('infuusio')) return copy[language].form_infusionPowder;
  if (value.includes('jauhe') && value.includes('oraaliliuos')) return copy[language].form_oralSolutionPowder;
  if (value.includes('jauhe') && value.includes('oraalisuspensio')) return copy[language].form_oralSuspensionPowder;
  const found=forms.findIndex(part => value.includes(part)); return found >= 0 ? copy[language]['form_'+found] : copy[language].otherForm;
}
function packText(e) { return (e.pack_label && e.pack_label[language]) || e.pack || ''; }
function formAndPack(e) {
  const form=formText(e.form), pack=packText(e);
  // A pack such as "98 tablets" already names the form, so the form is not repeated.
  return form.length > 3 && pack.toLocaleLowerCase().includes(form.toLocaleLowerCase().slice(0,-1)) ? [strengthShown(e),pack] : [form,strengthShown(e),pack];
}
function groupName(atc, lang = language) {
  const key = atc?.startsWith('S01') ? 'eye' : atc?.startsWith('S02') ? 'ear' : (atc || '')[0];
  return copy[lang]['group_'+key] || copy[lang].noGroup;
}
function card(e, now) {
  const t=copy[language], start=parsedDate(e.UnavailableFrom), end=parsedDate(e.EndingDate), upcoming=start && start.valueOf()>now;
  const days=start ? Math.floor((now-start.valueOf())/86400000) : null;
  const status=!start ? t.startUnknown : upcoming ? t.soon : t.out;
  const sentence=start ? `${upcoming ? t.starts : t.since} ${dateText(e.UnavailableFrom)}${!upcoming ? ` (${t.days(days)})` : ''}.` : t.startUnknownSentence;
  const late=end && end.valueOf()<now;
  const expectation=end ? `${t.expected} ${dateText(e.EndingDate)} (${t.estimate}).` : t.unknown;
  const group=groupName(e.atc);
  const details=[[t.form,e.form],[t.strength,strengthText(e)],[t.substance,e.substances],['ATC',e.atc],['VNR',e.NordicArticleNumber],[t.company,e.Company],[t.reported,e.DateOfTheNotification ? dateText(e.DateOfTheNotification) : '']];
  return `<article class="row"><div class="card-heading"><h3>${esc(e.name || t.unavailable)}</h3><span class="status ${upcoming ? 'upcoming' : ''}">${esc(status)}</span>${(e.atc || '').startsWith('Q') ? `<span class="vet">${esc(t.veterinary)}</span>` : ''}</div><p class="form">${esc(formAndPack(e).filter(Boolean).join(' · '))}</p><p class="group">${esc(t.group)}: ${esc(group)}</p><p class="status-sentence">${esc(sentence)}</p><p>${esc(expectation)} ${late ? `<strong class="late">${esc(t.late)}.</strong>` : ''}</p><p class="ask">${esc(t.askPharmacy)}</p><details><summary>${esc(t.details)}</summary><dl>${details.map(([label,value])=>`<div><dt>${esc(label)}</dt><dd>${esc(value || '—')}</dd></div>`).join('')}</dl><p class="more-info">${esc(t.moreInfo(e.Company))} <a href="${t.moreInfoUrl}">${esc(t.moreInfoLink)} ↗</a></p></details></article>`;
}
function drawList() {
  const t=copy[language], query=$('search').value;
  const rows=data.events.filter(e=>!e.removed_on && searchMatches(e,query));
  const sort=$('sort').value; rows.sort((a,b)=>sort==='name' ? (a.name || '').localeCompare(b.name || '',language) : sort==='longest' ? (a.UnavailableFrom || '9999').localeCompare(b.UnavailableFrom || '9999') : (b.UnavailableFrom || '').localeCompare(a.UnavailableFrom || ''));
  $('result-count').textContent=t.count(rows.length);
  const now=todayUTC();
  $('jump').hidden=!query.trim(); $('jump').textContent=`${t.count(rows.length)} · ${t.jump}`;
  $('list').innerHTML=rows.slice(0,visible).map(e=>card(e,now)).join('') || `<p class="list-state">${esc(t.empty)}</p>`;
  $('more').textContent=t.more; $('more').hidden=visible>=rows.length;
}
function setLanguage() {
  language=$('language').value; const t=copy[language];
  document.documentElement.lang=language; document.title=t.pageTitle;
  document.querySelector('meta[name="description"]').content=t.description;
  document.querySelectorAll('[data-i18n]').forEach(el => el.textContent=t[el.dataset.i18n]);
  document.querySelectorAll('[data-i18n-aria]').forEach(el => el.setAttribute('aria-label',t[el.dataset.i18nAria]));
  $('help-title').textContent=t.helpTitle; $('help-text').textContent=t.help; $('list-title').textContent=t.title; $('search-hint').textContent=t.hint; $('search').placeholder=t.placeholder; $('search').setAttribute('aria-label',t.searchLabel);
  try { localStorage.setItem('language',language); } catch (_) {}
  if(data) renderData(); else if (loadFailed) { $('updated').textContent=t.loadError; $('list').innerHTML=`<p class="list-state">${esc(t.listError)} <a href="https://fimea.fi/en/about_us/open-data">${esc(t.sourceError)}</a></p>`; } else { $('updated').textContent=t.loadingData; $('list').textContent=t.loading; $('delay-note').textContent=t.delayEmpty; }
}
let loadFailed=false;
try { const q=queryFromUrl(location.search); if (q) $('search').value=q; } catch (_) {}
$('language').value=language;
$('language').addEventListener('change',setLanguage);
setLanguage();
document.documentElement.classList.remove('i18n-pending');
function bars(id, counts, limit) {
  const entries = Object.entries(counts).sort((a,b) => b[1]-a[1]).slice(0,limit), max = entries[0]?.[1] || 1;
  $(id).innerHTML = entries.map(([name,n]) => `<div class="barrow"><span title="${esc(name)}">${esc(name)}</span><span class="track"><svg viewBox="0 0 100 1" preserveAspectRatio="none" aria-hidden="true"><rect width="${n/max*100}" height="1" fill="#2b927b"/></svg></span><strong>${numberText(n)}</strong></div>`).join('');
}
function drawChart(history, maxGap) {
  const t=copy[language];
  if (history.length < 2) { $('chart').textContent=t.chartEmpty; return; }
  const day=h=>Date.parse(h.date)/86400000, segments=[];
  history.forEach(h=>{const g=segments[segments.length-1]; if(g && day(h)-day(g[g.length-1])<=maxGap) g.push(h); else segments.push([h]);});
  const lo=0, hi=Math.max(50,Math.ceil(Math.max(...history.map(h=>h.count))/50)*50), y=n=>150-125*n/hi;
  const band=Math.min(26,150/Math.max(1,segments.length-1)), room=350-band*(segments.length-1), spans=segments.map(g=>Math.max(day(g[g.length-1])-day(g[0]),1)), sum=spans.reduce((a,b)=>a+b,0), minimum=Math.min(14,room/segments.length/2);
  const widths=spans.map(s=>minimum+(room-minimum*segments.length)*s/sum); let x0=40, svg='', gaps=[];
  segments.forEach((g,i)=>{
    const w=widths[i], x=h=>g.length===1 ? x0+w/2 : x0+w*(day(h)-day(g[0]))/(day(g[g.length-1])-day(g[0]));
    if(g.length>1) svg+=`<polyline points="${g.map(h=>`${x(h).toFixed(1)},${y(h.count).toFixed(1)}`).join(' ')}" fill="none" stroke="#16806d" stroke-width="1.5" vector-effect="non-scaling-stroke"/>`;
    svg+=g.map(h=>`<circle cx="${x(h).toFixed(1)}" cy="${y(h.count).toFixed(1)}" r="2.6" fill="${h.imported ? '#f7f8f3' : '#16806d'}" stroke="#16806d" stroke-width="1.2"><title>${esc(t.capturePoint(dateText(h.date),numberText(h.count),h.imported ? t.importedSource : t.savedSource))}</title></circle>`).join('');
    x0+=w;
    if(i<segments.length-1) {const days=Math.round(day(segments[i+1][0])-day(g[g.length-1])); gaps.push(numberText(days)); svg+=`<rect x="${x0}" y="10" width="${band}" height="140" fill="#e8f0e9"/>`; x0+=band;}
  });
  const grid=`<text x="36" y="${y(hi)+5}" font-size="14" fill="#536b5e" text-anchor="end">${numberText(hi)}</text><text x="36" y="155" font-size="14" fill="#536b5e" text-anchor="end">${numberText(lo)}</text>`, last=history[history.length-1];
  $('chart').innerHTML=`<svg viewBox="0 0 400 170" role="img" aria-label="${esc(t.chartSummary(dateText(history[0].date),dateText(last.date),numberText(last.count),gaps.join(', ')))}">${grid}${svg}</svg><div class="chart-labels"><span>${esc(dateText(history[0].date))}</span><span>${numberText(last.count)} · ${esc(dateText(last.date))}</span></div><div class="chart-labels"><span>${esc(t.savedLegend)}</span><span>${esc(t.importedLegend)}</span></div>${gaps.length ? `<div class="chart-labels"><span>${esc(gaps.map(g=>t.noCaptures(g)).join('; '))}</span></div>` : ''}`;
}
function drawWeek(w, total) {
  const t=copy[language], n=numberText; $('feed-link').href=language==='fi' ? 'feed-fi.xml' : 'feed.xml';
  if (!w) { $('week').hidden=true; return; }
  const from=dateText(w.from); $('week').hidden=false;
  $('week-window').textContent=t.weekWindow(from,n(w.days));
  $('week-new-label').textContent=t.weekNew; $('week-new').textContent=n(w.new); $('week-new-note').textContent=t.weekNewNote(from);
  $('week-left-label').textContent=t.weekLeft; $('week-left').textContent=n(w.left); $('week-left-note').textContent=t.weekLeftNote(from);
  $('week-total-label').textContent=t.weekTotal; $('week-total').textContent=n(total); $('week-total-note').textContent=t.weekTotalNote(n(total),n(w.count_from),from);
}
function drawDelays(d, snapshotDate) {
  const t=copy[language]; if(!d) { $('delay-headline').textContent=''; $('delay-visual').innerHTML=''; $('delay-note').textContent=t.delayEmpty; $('delay-list').innerHTML=''; $('how-count').hidden=true; return; }
  const n=numberText, pct=s=>`${Math.round(s*100)}${language === 'fi' ? ' ' : ''}%`;
  $('delay-headline').textContent=d.meaningful ? t.delayHeadline(n(d.past_estimate),n(d.sample_size),n(d.undetermined),pct(d.share_past_min),pct(d.share_past_max)) : t.delaySample(n(d.sample_size),n(d.max_gap_days))+t.delaySmall(n(d.min_sample));
  const values=[[t.delayBy,d.not_past_estimate],[t.delayPast,d.past_estimate],[t.delayUncertain,d.undetermined]], max=Math.max(...values.map(([,v])=>v),1);
  $('delay-visual').innerHTML=(d.meaningful ? `<div class="delay-bars">${values.map(([label,value])=>`<div class="delay-row"><span>${esc(label)}</span><svg viewBox="0 0 100 1" preserveAspectRatio="none" aria-hidden="true"><rect width="100" height="1" fill="#e3ece4"/><rect width="${value/max*100}" height="1" fill="#157965"/></svg><strong>${n(value)}</strong></div>`).join('')}</div>` : '')+`<p>${esc(t.activePast(n(d.active_past_estimate),dateText(snapshotDate),n(d.max_gap_days)))}</p>`;
  $('delay-note').textContent=t.delayMethod(n(d.sample_size),n(d.max_gap_days))+t.delayBias;
  const x=d.excluded || {}; $('how-count').hidden=false;
  const skipped=[['listed_at_first_capture',t.howFirst],['no_estimate',t.howNoEstimate],['wide_start_window',t.howStart],['wide_removal_window',t.howEnd],['vnr_still_listed',t.howChanged]].filter(([k])=>x[k]).map(([k,f])=>f(n(x[k]))).join(', ');
  $('how-count-text').textContent=t.howText(n(d.sample_size),n(d.removed_total),n(d.max_gap_days),skipped);
  $('delay-list').innerHTML=d.meaningful && d.examples.length ? `<h3>${esc(t.delayExamples)}</h3>`+d.examples.map(e=>`<p>${esc(nameWithStrength(e) || e.vnr)} · ${esc(t.firstEstimate)} ${esc(dateText(e.first_estimated_end))} · ${esc(t.lastListed)} ${esc(dateText(e.last_seen))} · ${esc(t.goneBy)} ${esc(dateText(e.removed_on))}</p>`).join('') : '';
}
function drawDates(d) {
  const meta = d.source_metadata || {}, sourceTimes = [];
  if (meta.shortages_last_modified && timestampText(meta.shortages_last_modified)) sourceTimes.push(`${copy[language].shortageFile}: ${timestampText(meta.shortages_last_modified)}`);
  if (meta.register_last_modified && timestampText(meta.register_last_modified)) sourceTimes.push(`${copy[language].register}: ${timestampText(meta.register_last_modified)}`);
  $('source-times').textContent = sourceTimes.join('; ');
  $('citation').textContent=copy[language].citation(dateText(d.snapshot_date),formatDate(new Date(todayUTC()))); $('cite-box').hidden=false;
  const newer=parsedDate(d.last_checked) && parsedDate(d.snapshot_date) && d.snapshot_date>d.last_checked;
  const freshness=freshnessInfo(d); $('freshness').textContent=newer ? '' : freshness.text+(freshness.stale ? ` · ${freshness.warning}` : ''); $('freshness').className=!newer && freshness.stale ? 'fresh-warning' : '';
  $('updated').textContent = newer ? copy[language].updated(dateText(d.snapshot_date)) : copy[language].latest(dateText(d.snapshot_date)); $('start').textContent = dateText(d.archive_start);
  if (!historyData) { if(historyFailed) { $('history-note').innerHTML=`${esc(copy[language].historyError)} <a href="https://fimea.fi/en/about_us/open-data">${esc(copy[language].sourceError)}</a>`; $('delay-note').textContent=copy[language].historyError; } return; }
  const h=historyData, t=copy[language], own=h.history.filter(x=>!x.imported).length, imported=h.history.length-own;
  const gaps=h.history.filter(x=>x.gap_days>h.max_gap_days).map(x=>t.gapBefore(numberText(x.gap_days),dateText(x.date)));
  $('history-note').textContent=t.historySummary(numberText(h.history.length),dateText(d.archive_start),numberText(imported),numberText(own),gaps.join('; '),numberText(h.first_capture_count));
  const rss=(h.rss_counts || []).filter(c=>c.items);
  $('rss-note').textContent=rss.length ? t.rssSummary(rss.map(c=>t.rssItem(dateText(c.date),numberText(c.items))).join('; ')) : '';
  drawChart(h.history,h.max_gap_days); drawDelays(h.delays,d.snapshot_date);
}
function renderData() {
  const d=data, t=copy[language], current=d.events.filter(e => !e.removed_on), companies={}, atc={};
  current.forEach(e => {const company=e.Company || t.unknownCompany; companies[company]=(companies[company] || 0)+1; const group=e.atc && groupName(e.atc); if(group) atc[group]=(atc[group] || 0)+1;});
  drawDates(d); $('total').textContent=numberText(current.length); $('companies').textContent=numberText(Object.keys(companies).length);
  const now=todayUTC(); const longest=current.filter(e=>parsedDate(e.UnavailableFrom) && parsedDate(e.UnavailableFrom).valueOf()<=now).sort((a,b)=>a.UnavailableFrom.localeCompare(b.UnavailableFrom)).slice(0,5);
  $('longest-list').innerHTML=longest.map(e=>{const duration=t.days(Math.floor((now-parsedDate(e.UnavailableFrom).valueOf())/86400000)).replace(/ /g,'\u00a0'); return `<li><div><strong>${esc(nameWithStrength(e) || t.unavailable)}</strong><small>${esc([packText(e),e.Company].filter(Boolean).join(' · '))}</small><small>${esc(t.since)} ${esc(dateText(e.UnavailableFrom))}</small></div><span class="duration">${esc(duration)}</span></li>`;}).join('');
  drawWeek(weekData,current.length); bars('atc',atc,30); bars('company',companies,10); drawList();
}
fetch('current.json').then(r => {if (!r.ok) throw Error(); return r.json()}).then(d => {data=d; renderData(); requestAnimationFrame(()=>{fetch('history.json').then(r=>{if(!r.ok) throw Error(); return r.json()}).then(h=>{historyData=h; renderData();}).catch(()=>{historyFailed=true; renderData();}); fetch('week.json').then(r=>{if(!r.ok) throw Error(); return r.json()}).then(w=>{weekData=w; renderData();}).catch(()=>{});});}).catch(() => {data=undefined; loadFailed=true; setLanguage();});
let urlTimer;
function syncUrl() { try { const url=new URL(location.href), q=$('search').value.trim().slice(0,100); if (q) url.searchParams.set('q',q); else url.searchParams.delete('q'); history.replaceState(null,'',url); } catch (_) {} }
$('search').addEventListener('input', () => {visible=50; if(data) drawList(); clearTimeout(urlTimer); urlTimer=setTimeout(syncUrl,400)});
$('search').addEventListener('keydown', e => {if (e.key==='Enter') {e.preventDefault(); $('shortages').scrollIntoView(); $('shortages').focus({preventScroll:true});}});
function selectCitation() { const range=document.createRange(); range.selectNodeContents($('citation')); const selection=getSelection(); selection.removeAllRanges(); selection.addRange(range); }
$('copy-cite').addEventListener('click', () => {const done=()=>{$('copy-status').textContent=copy[language].copied; setTimeout(()=>{$('copy-status').textContent='';},2500);}; if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText($('citation').textContent).then(done,selectCitation); else selectCitation();}); $('more').addEventListener('click', () => {visible+=50; drawList()});

$('sort').addEventListener('change', () => {visible=50; if(data) drawList();});
document.documentElement.dataset.appReady='true';
