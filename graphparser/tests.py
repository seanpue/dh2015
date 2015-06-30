import graphparser

nagarip = graphparser.GraphParser('settings/devanagari.yaml')
urdup = graphparser.GraphParser('settings/urdu.yaml')

def test_nagari():
    assert nagarip.parse('kyaa').output==u'\u0915\u094d\u092f\u093e'
    
def test_urdu():
    assert urdup.parse("kih us kaa").output==u'\u06a9\u06c1 \u0627\u0633 \u06a9\u0627'