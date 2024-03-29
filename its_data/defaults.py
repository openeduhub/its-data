from collections.abc import Collection
from enum import Enum

from its_data.data import Basic_Value, Basic_Value_Not_None
from its_data.evaluation import eval_classification, Evaluation


class Fields(Enum):
    """A selection of commonly used metadata fields."""

    AGE = "properties.ccm:educationaltypicalagerange"
    COURSE_MODE = "properties.ccm:oeh_course_coursemode"
    COLLECTIONS_LOCATION = "collections.properties.cclom:location"
    COLLECTIONS_TITLE = "collections.properties.cm:title"
    COLLECTIONS_UUID = "collections.properties.sys:node-uuid"
    COMPETENCE = "properties.ccm:competence"
    DESCRIPTION = "properties.cclom:general_description"
    DURATION = "properties.cclom:duration"
    EDUCATIONAL_CONTEXT = "properties.ccm:educationalcontext"
    FSK_RATING = "properties.ccm:fskRating"
    ID = "nodeRef.id"
    INTENDED_ENDUSER = "properties.ccm:educationalintendedenduserrole"
    KEYWORDS_CONTROLLED = "properties.cclom:classification_keyword"
    KEYWORDS_FREE = "properties.cclom:general_keyword"
    LANGUAGE = "properties.cclom:general_language"
    LRT = "properties.ccm:oeh_lrt"
    TAXONID = "properties.ccm:taxonid"
    TAXONID_UNIVERSITY = "properties.ccm:oeh_taxonid_university"
    TEST_DATA = "properties.ccm:oeh_ai_test_data"
    TITLE = "properties.cclom:title"
    TOPIC = "properties.ccm:curriculum"
    URL = "properties.ccm:wwwurl"


#: Default values that shall be dropped from particular metadata fields.
dropped_values: dict[str, Collection[Basic_Value_Not_None]] = {
    Fields.TAXONID.value: {
        "",
        "http://w3id.org/openeduhub/vocabs/discipline/???",
        "http://w3id.org/openeduhub/vocabs/discipline/Pädagogik",  # ambiguous
    },
    Fields.LANGUAGE.value: set(),
}

#: Default values that shall be remapped for particular metadata fields
remapped_values: dict[str, dict[Basic_Value_Not_None, Basic_Value]] = {
    Fields.TAXONID.value: {
        "http://w3id.org/openeduhub/vocabs/discipline/Darstellendes-Spiel": "http://w3id.org/openeduhub/vocabs/discipline/12002",
        "http://w3id.org/openeduhub/vocabs/discipline/Deutsch": "http://w3id.org/openeduhub/vocabs/discipline/120",
        "http://w3id.org/openeduhub/vocabs/discipline/Deutsch als Zweitsprache": "http://w3id.org/openeduhub/vocabs/discipline/28002",
        "http://w3id.org/openeduhub/vocabs/discipline/Deutsch als": "http://w3id.org/openeduhub/vocabs/discipline/28002",
        "Zweitsprache": "http://w3id.org/openeduhub/vocabs/discipline/28002",
        "http://w3id.org/openeduhub/vocabs/discipline/Englisch": "http://w3id.org/openeduhub/vocabs/discipline/20001",
        "http://w3id.org/openeduhub/vocabs/discipline/Geografie": "http://w3id.org/openeduhub/vocabs/discipline/220",
        "http://w3id.org/openeduhub/vocabs/discipline/Geschichte": "http://w3id.org/openeduhub/vocabs/discipline/240",
        "http://w3id.org/openeduhub/vocabs/discipline/Informatik": "http://w3id.org/openeduhub/vocabs/discipline/320",
        "http://w3id.org/openeduhub/vocabs/discipline/Mathematik": "http://w3id.org/openeduhub/vocabs/discipline/380",
        "http://w3id.org/openeduhub/vocabs/discipline/Physik": "http://w3id.org/openeduhub/vocabs/discipline/460",
        "http://w3id.org/openeduhub/vocabs/discipline/Religion": "http://w3id.org/openeduhub/vocabs/discipline/520",
        "http://w3id.org/openeduhub/vocabs/discipline/Spanisch": "http://w3id.org/openeduhub/vocabs/discipline/20007",
        "http://w3id.org/openeduhub/vocabs/discipline/Medienbildung": "http://w3id.org/openeduhub/vocabs/discipline/900",
        "http://w3id.org/openeduhub/vocabs/discipline/Physik": "http://w3id.org/openeduhub/vocabs/discipline/460",
        "http://w3id.org/openeduhub/vocabs/discipline/Mathematik": "http://w3id.org/openeduhub/vocabs/discipline/380",
    },
    Fields.LANGUAGE.value: {
        "de_DE": "de",
        "de_AT": "de",
        "DE": "de",
        "de-DE": "de",
        "Deutsch": "de",
        "en-US-LEARN": "en",
        "en_US": "en",
        "en_GB": "en",
        "hu_HU": "hu",
        "es_CR": "es",
        "es_ES": "es",
        "es_AR": "es",
        "fr_FR": "fr",
        "tr_TR": "tr",
        "latin": "la",
    },
}

#: Default SKOS controlled vocabularies to look up label definition in
#: for particular metadata fields.
skos_urls: dict[str, str] = {
    Fields.EDUCATIONAL_CONTEXT.value: "https://vocabs.openeduhub.de/w3id.org/openeduhub/vocabs/educationalContext/index.json",
    Fields.FSK_RATING.value: "https://vocabs.openeduhub.de/w3id.org/openeduhub/vocabs/fskRating/index.json",
    Fields.INTENDED_ENDUSER.value: "https://vocabs.openeduhub.de/w3id.org/openeduhub/vocabs/intendedEndUserRole/index.json",
    Fields.LRT.value: "https://vocabs.openeduhub.de/w3id.org/openeduhub/vocabs/new_lrt/index.json",
    Fields.TAXONID.value: "https://vocabs.openeduhub.de/w3id.org/openeduhub/vocabs/discipline/index.json",
    Fields.TOPIC.value: "https://vocabs.openeduhub.de/w3id.org/openeduhub/vocabs/oeh-topics/5e40e372-735c-4b17-bbf7-e827a5702b57.json",
}

#: Default evaluation functions that are relevant to the particular metadata field.
evaluation_functions: dict[str, Evaluation] = {
    field.value: eval_classification
    for field in [
        Fields.COURSE_MODE,
        Fields.EDUCATIONAL_CONTEXT,
        Fields.FSK_RATING,
        Fields.INTENDED_ENDUSER,
        Fields.KEYWORDS_CONTROLLED,
        Fields.TAXONID,
        Fields.TAXONID_UNIVERSITY,
        Fields.LANGUAGE,
    ]
}
