import csv
import re
import json
import requests
import sys
import orodja

vzorec_bloka = re.compile(
    r'<div class="lister-item mode-advanced">.*?'
    r'</p>\s*</div>\s*</div>',
    flags=re.DOTALL
)

vzorec_filma = re.compile(
    r'<a href="/title/tt(?P<id>\d+)/.*?".*?'
    r'img alt="(?P<naslov>.+?)".*?'
    r'lister-item-year text-muted unbold">\((?P<leto>.*?)\)</span>.*?'
    r'runtime">(?P<dolzina>\d+?) min</.*?'
    r'<span class="genre">(?P<zanri>.*?)</span>.*?'
    r'<strong>(?P<ocena>.+?)</strong>.*?'
    r'<p class="text-muted">(?P<opis>.+?)</p.*?'
    r'Votes:.*?data-value="(?P<glasovi>\d+)"'
    , flags=re.DOTALL
)

vzorec_osebe = re.compile(
    r'<a\s+href="/name/nm(?P<id>\d+)/?[^>]*?>(?P<ime>.+?)</a>',
    flags=re.DOTALL
)

vzorec_povezave = re.compile(
    r'<a.*?>(.+?)</a>',
    flags=re.DOTALL
)

vzorec_zasluzka = re.compile(
    r'Gross:.*?data-value="(?P<zasluzek>(\d|,)+)"',
    flags=re.DOTALL
)

vzorec_metascore = re.compile(
    r'<span class="metascore.*?">(?P<metascore>\d+)',
    flags=re.DOTALL
)

vzorec_oznake = re.compile(
    r'<span class="certificate">(?P<oznaka>.+?)</span>',
    flags=re.DOTALL
)

vzorec_daljsi_povzetek = re.compile(
    r'<a href="/title/tt\d+/plotsummary.*?&nbsp;&raquo;',
    flags=re.DOTALL
)

vzorec_igralcev = re.compile(
    r'Stars?:(?P<igralci>.+?)</p>.*?',
    flags=re.DOTALL
)


def izloci_osebe(niz):
    osebe = []
    for oseba in vzorec_osebe.finditer(niz):
        osebe.append({
            'id': int(oseba.groupdict()['id']),
            'ime': oseba.groupdict()['ime'],
        })
    return osebe


def izloci_podatke_filma(blok):
    film = vzorec_filma.search(blok).groupdict()
    film['id'] = int(film['id'])
    film['dolzina'] = int(film['dolzina'])
    film['zanri'] = film['zanri'].strip().split(', ')
    film['leto'] = film['leto'].replace('(', '')
    film['leto'] = film['leto'].replace('- ', '2022')
    film['leto'] = film['leto'].replace(')', '')
    film['leto'] = film['leto'].replace(' ', '')
    film['leto'] = film['leto'].replace('I', '')
    film['leto'] = film['leto'].replace('V', '')
    film['leto'] = film['leto'].replace('X', '')
    #film['leto'] = film['leto'].replace(r"[A-Z]", '') nevem zkj to ne dela
    film['leto-zacetek'] = int((film['leto'].split('–')[0]))
    if (len(film['leto'].split('–')) == 2) :
        #print (film['leto'].split('–')[1])
        try:
            film['leto-konec'] = int(film['leto'].split('–')[1])
        except:
            film['leto-konec'] = 2022 # ko bo leto 2022 spremen na 2023

    else:
        film['leto-konec'] = int((film['leto'].split('–')[0]))
    # odstranimo morebitno povezavo na daljši posnetek
    film['opis'] = vzorec_daljsi_povzetek.sub('', film['opis'])
    # odstranimo morebitne povezave v opisu
    film['opis'] = vzorec_povezave.sub(r'\1', film['opis'])
    film['opis'] = film['opis'].strip()
    film['ocena'] = float(film['ocena'])
    film['glasovi'] = int(film['glasovi'])

    # zabeležimo oznako, če je omenjena
    oznaka = vzorec_oznake.search(blok)
    if oznaka:
        film['oznaka'] = oznaka['oznaka']
    else:
        film['oznaka'] = None
    # zabeležimo igralce, če so omenjeni
    igralci = vzorec_igralcev.search(blok)
    if igralci:
        film['igralci'] = izloci_osebe(igralci['igralci'])
    else:
        film['igralci'] = []
    # zabeležimo zaslužek, če je omenjen
    zasluzek = vzorec_zasluzka.search(blok)
    if zasluzek:
        film['zasluzek'] = int(zasluzek['zasluzek'].replace(',', ''))
    else:
        film['zasluzek'] = None
    # zabeležimo metascore, če je omenjen
    metascore = vzorec_metascore.search(blok)
    if metascore:
        film['metascore'] = int(metascore['metascore'])
    else:
        film['metascore'] = None
    return film

count = 0

def ime_datoteke(st_strani):
    return f"naj-filmi/najboljsi-filmi-{st_strani}.html"

def Potegni_page_dol():
    for st_strani in range(40):
        url = (
        f'https://www.imdb.com/search/title/?title_type=tv_series&'
        f'sort=num_votes,desc&title_type=feature&count=250'
        f'&start={(st_strani) *250}'
    )
        print(f"Zajemam {url}")
        response = requests.get(url, headers={
         # "Accept-Language": "sl-si"
     })
        vsebina = response.text
        with open(ime_datoteke(st_strani), 'w') as dat:
             dat.write(vsebina)

################################
#Potegni_page_dol()

def izloci_gnezdene_podatke(filmi):
    REZISER, IGRALEC = 'R', 'I'
    osebe, vloge, zanri = [], [], []
    videne_osebe = set()

    def dodaj_vlogo(film, oseba, vloga, mesto):
        if oseba['id'] not in videne_osebe:
            videne_osebe.add(oseba['id'])
            osebe.append(oseba)
        vloge.append({
            'film': film['id'],
            'oseba': oseba['id'],
            'mesto': mesto,
        })


    for film in filmi:
        for zanr in film.pop('zanri'):
            zanri.append({'film': film['id'], 'zanr': zanr})
        for mesto, oseba in enumerate(film.pop('igralci'), 1):
            dodaj_vlogo(film, oseba, IGRALEC, mesto)

    osebe.sort(key=lambda oseba: oseba['id'])
    vloge.sort(key=lambda vloga: (vloga['film'], vloga['mesto']))
    zanri.sort(key=lambda zanr: (zanr['film'], zanr['zanr']))

    return osebe, vloge, zanri


filmi = []
st_strani = 0
while st_strani < 40 :
    #print(st_strani) # to se zgodi po 10.000 kodiranja
    while st_strani in [3,13,16,17,18,19,20,23,27,29,30,31,32,34,35,39,40]:
        st_strani += 1 
        
    if st_strani >= 40:
            break

    print(st_strani)
    with open(ime_datoteke(st_strani)) as dat:
        vsebina = dat.read()
    for blok in vzorec_bloka.finditer(vsebina):
        filmi.append(izloci_podatke_filma(blok.group(0)))

    st_strani += 1

with open("filmi.json", "w") as dat:
    json.dump(filmi, dat, indent=4, ensure_ascii=False)

with open("filmi.csv", "w") as dat:
    writer = csv.DictWriter(dat, [
        "id",
        "naslov",
        "leto",
        "leto-zacetek",
        "leto-konec",
        "zasluzek",
        "glasovi",
        "dolzina",
        "metascore",
        "oznaka",
        "opis",
        "ocena",
        "igralci",
        "zanri",
    ])
    writer.writeheader()
    writer.writerows(filmi)



filmi.sort(key=lambda film: film['id'])
orodja.zapisi_json(filmi, 'obdelani-podatki/filmi.json')
osebe, vloge, zanri = izloci_gnezdene_podatke(filmi)
orodja.zapisi_csv(
    filmi,
    ['id', 'naslov',"leto-zacetek",
        "leto-konec", 'dolzina', 'leto', 'ocena', 'metascore', 'glasovi', 'zasluzek', 'oznaka', 'opis'], 'obdelani-podatki/filmi1.csv'
)
orodja.zapisi_csv(osebe, ['id', 'ime'], 'obdelani-podatki/osebe.csv')
orodja.zapisi_csv(vloge, ['film', 'oseba', 'mesto'], 'obdelani-podatki/igralce.csv')
orodja.zapisi_csv(zanri, ['film', 'zanr'], 'obdelani-podatki/zanri.csv')
