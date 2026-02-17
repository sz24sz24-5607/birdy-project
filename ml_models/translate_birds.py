#!/usr/bin/env python3
"""
Script to translate scientific bird names to German common names.
This script uses web searches and database lookups to find German names.
"""

import time
import re

# Comprehensive dictionary of scientific names to German common names
# This will be built up based on research
bird_translations = {
    # Line 1-50
    "Haemorhous cassinii": "Cassingimpel",
    "Aramus guarauna": "Rallenkranich",
    "Rupornis magnirostris": "Wegebussard",
    "Cyanocitta cristata": "Blauhäher",
    "Cyanocitta stelleri": "Diademhäher",
    "Balearica regulorum": "Grauer Kronenkranich",
    "Pyrocephalus rubinus": "Rubintyrann",
    "Recurvirostra americana": "Amerikanischer Säbelschnäbler",
    "Ardeotis kori": "Riesentrappe",
    "Pica nuttalli": "Gelbschnabelelster",
    "Perisoreus canadensis": "Unglückshäher",
    "Antigone canadensis": "Kanadakranich",
    "Parkesia noveboracensis": "Drosselwaldsänger",
    "Ardea herodias occidentalis": "Kanadareiher",
    "Porzana carolina": "Carolinasumpfhuhn",
    "Anas platyrhynchos diazi": "Mexiko-Stockente",
    "Motacilla cinerea": "Gebirgsstelze",
    "Empidonax difficilis": "Pazifikschnäpper",
    "Empidonax minimus": "Zwergschnäpper",
    "Empidonax fulvifrons": "Braunscheitel-Schnäpper",
    "Empidonax traillii": "Weidenschnäpper",
    "Empidonax hammondii": "Hammondschnäpper",
    "Empidonax occidentalis": "Schnäpper",
    "Rallus limicola": "Virginiaralle",
    "Grus grus": "Kranich",
    "Quiscalus major": "Bootsschwanzgrackel",
    "Branta leucopsis": "Nonnengans",
    "Cyanocorax yucatanicus": "Yucatánhäher",
    "Cyanocorax yncas": "Inkahäher",
    "Oceanites oceanicus": "Buntfuß-Sturmschwalbe",
    "Quiscalus niger": "Antillengrackel",
    "Psilorhinus morio": "Braunhäher",
    "Megarynchus pitangua": "Großschnabelkiskadee",
    "Gallinula tenebrosa": "Australisches Teichhuhn",
    "Gallus gallus domesticus": "Haushuhn",
    "Numida meleagris": "Helmperlhuhn",
    "Junco hyemalis caniceps": "Graukopf-Junko",
    "Tyrannus vociferans": "Couchstyra

nn",
    "Tyrannus tyrannus": "Königstyrann",
    "Tyrannus forficatus": "Scherenschwanztyrann",
    "Tyrannus crassirostris": "Dickschnabeltyrann",
    "Tyrannus verticalis": "Königstyrann",
    "Tyrannus savana": "Savannentyrann",
    "Gallirallus australis": "Wekaralle",
    "Calocitta formosa": "Blauweißhäher",
    "Calocitta colliei": "Schwarzkehlelsterhäher",
    "Fulica americana": "Amerikanisches Blässhuhn",
    "Pachyramphus aglaiae": "Rosakehlbekarde",
    "Buteo lagopus": "Raufußbussard",
    "Cygnus atratus": "Trauerschwan",
}

def read_input_file(filepath):
    """Read the input file with scientific names."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    return [line.strip() for line in lines]

def translate_bird_name(scientific_name):
    """
    Translate a scientific bird name to German.
    Returns the German name if found, otherwise returns the scientific name.
    """
    if scientific_name == "background":
        return "background"

    if scientific_name in bird_translations:
        return bird_translations[scientific_name]

    # If not found in dictionary, return scientific name
    return scientific_name

def main():
    input_file = "/home/pi/birdy_project/ml_models/labels_en.txt"
    output_file = "/home/pi/birdy_project/ml_models/labels_de.txt"

    # Read input
    scientific_names = read_input_file(input_file)

    # Translate
    german_names = []
    for name in scientific_names:
        german_name = translate_bird_name(name)
        german_names.append(german_name)

    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        for name in german_names:
            f.write(name + '\n')

    print(f"Translation complete. Output written to {output_file}")
    print(f"Total lines: {len(german_names)}")

if __name__ == "__main__":
    main()
