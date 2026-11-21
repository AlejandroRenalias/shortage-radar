"""Readable pack sizes from the register's pack text, unit and Finnish form."""
import re

# (Finnish form keyword, English singular, English plural, Finnish nominative, Finnish partitive plural).
# The first keyword found in the form wins, so specific forms come first.
COUNT_NOUNS = [
    ('annospussi', 'sachet', 'sachets', 'annospussi', 'annospussia'),
    ('peräpuikko', 'suppository', 'suppositories', 'peräpuikko', 'peräpuikkoa'),
    ('laastari', 'patch', 'patches', 'laastari', 'laastaria'),
    ('kapseli', 'capsule', 'capsules', 'kapseli', 'kapselia'),
    ('tabletti', 'tablet', 'tablets', 'tabletti', 'tablettia'),
    ('bletti', 'tablet', 'tablets', 'tabletti', 'tablettia'),
]
# Register unit -> (English singular, English plural, Finnish singular, Finnish plural); None means keep the unit as written.
UNIT_NOUNS = {
    'kpl': ('pc', 'pcs', 'kpl', 'kpl'),
    'annos': ('dose', 'doses', 'annos', 'annosta'),
    'annosta': ('dose', 'doses', 'annos', 'annosta'),
    'suihketta': ('spray', 'sprays', 'suihke', 'suihketta'),
}
# Words the register uses inside its own pack text, written for English readers.
ENGLISH_WORDS = {'annosta': 'doses', 'annos': 'dose', 'suihketta': 'sprays', 'kpl': 'pcs'}
PLAIN_COUNT = re.compile(r'\d+')
# Sums and multiples such as "11 + 42" or "3 x 28" get a noun only when the form is countable.
COMPOUND_COUNT = re.compile(r'\d+(?: *[+x] *\d+)+')
LETTERS = re.compile('[A-Za-zÅÄÖåäö]')


def _number(text, lang):
    return text.replace('.', ',') if lang == 'fi' else text


def pack_label(text, unit='', form=''):
    """Return {'en': ..., 'fi': ...} for a package, or empty strings when there is no pack text."""
    text, unit, form = ' '.join((text or '').split()), (unit or '').strip(), (form or '').lower()
    if not text:
        return {'en': '', 'fi': ''}
    noun = next((n for n in COUNT_NOUNS if n[0] in form), None)
    compound = COMPOUND_COUNT.fullmatch(text)
    if LETTERS.search(text) and not compound:
        # The register already gives a unit, so keep its wording.
        english = re.sub(r'[^\W\d_]+', lambda m: ENGLISH_WORDS.get(m.group(0), m.group(0)), text)
        return {'en': english, 'fi': _number(text, 'fi')}
    if not (PLAIN_COUNT.fullmatch(text) or (compound and noun and unit in ('', 'kpl'))):
        return {'en': text, 'fi': _number(text, 'fi')}
    plural = text != '1'
    if unit in ('', 'kpl') and noun:
        return {'en': f'{text} {noun[2] if plural else noun[1]}', 'fi': f'{text} {noun[4] if plural else noun[3]}'}
    if unit in UNIT_NOUNS:
        en_one, en_many, fi_one, fi_many = UNIT_NOUNS[unit]
        return {'en': f'{text} {en_many if plural else en_one}', 'fi': f'{text} {fi_many if plural else fi_one}'}
    if unit == '':
        return {'en': f'{text} pcs', 'fi': f'{text} kpl'}
    # Measured units such as ml, g or mg are the same in both languages.
    return {'en': f'{text} {unit}', 'fi': f'{text} {unit}'}


# Finnish unit words in a register strength, for English readers.
STRENGTH_WORDS = {'tuntia': 'hours', 'tunti': 'hour', 'annosta': 'dose', 'annos': 'dose', 'mikrog': 'microg', 'yksikköä': 'units', 'yksikkö': 'unit', 'vuorokautta': 'day', 'vuorokausi': 'day'}
STRENGTH_WORD = re.compile(r'(?<![^\W\d_])(' + '|'.join(STRENGTH_WORDS) + r')(?![^\W\d_])', re.IGNORECASE)


def strength_label(strength, lang):
    """A strength as written for a language: Finnish keeps the register wording with a decimal comma ("2,5 mg"); English translates common unit words."""
    text = ' '.join((strength or '').split())
    if lang == 'fi':
        return re.sub(r'(?<=\d)\.(?=\d)', ',', text)
    text = re.sub(r'(?<=\d )h(?![^\W\d_])', 'hours', text)
    return STRENGTH_WORD.sub(lambda m: STRENGTH_WORDS[m.group(1).lower()], text)


def name_with_strength(name, strength, lang, pack=''):
    """The medicine name followed by its strength, unless the name or the pack label already starts with it."""
    label = strength_label(strength, lang)
    pack, own = (pack or '').lower(), label.lower()
    if not label or (pack.startswith(own) and not re.match(r'[^\W_]|[.,]', pack[len(own):len(own) + 1])) or own in (name or '').lower():
        return name or ''
    return f'{name} {label}' if name else label
