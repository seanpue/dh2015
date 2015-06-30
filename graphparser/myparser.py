import re


def load_yaml(filename):
    """
    Reads any yaml file and returns it as object.
    """
    import yaml
    stream = file(filename)
    return yaml.load(stream)

debug=False
        
import unicodedata
def unescape_unicode_charnames(s):
    """
    Takes \N{charname} in production rule and turns to Unicode string.
    """
    
    def get_unicode_char(matchobj):
#            """
#            Returns Unicode character of \N{character name}
#            """
#           if debug: print "Trying "+matchobj+"in get_unicode_char"
        s = matchobj.group(0)
        m = re.match(r'\\N{(.+)}',s)
        char = unicodedata.lookup(m.group(1))
        return char

    return re.sub(r'\\N{.+?}',get_unicode_char,s)

def compare_rules(x,y):
    """
    Compares rules and sees which has more tokens or conditions (prev, next)
    """
    
    diff = 10*(len(y['tokens'])-len(x['tokens']))   
    if diff != 0:
        return diff
    (x_conds, y_conds) = (0,0)
    for cond in ('prev','next'):
        if cond in x: x_conds +=len(x[cond])
        if cond in y: y_conds +=len(y[cond])
    for cond in ('prev_classes', 'next_classes'):
        if cond in x: x_conds += len(x[cond])
        if cond in y: y_conds += len(y[cond])
    return y_conds - x_conds # see if one has  more <classes>


def onmatch_rules_from_yaml_data(rules_raw):
    ''' Some quick code to generate the onmatch rules. It only relies on classes '''
    ''' returns a tuple ( (left_classes,right_classes) , prod)
        rules are classes '''
    onmatch_rules = [] # clean list of rule
#    print "rules_r is"+str(rules_raw)
    debug=True

    match_rules = []
    for key in rules_raw:
        assert len(key)==1
        rule = key.keys()[0]
        prod_orig = key[rule]
        prod = unescape_unicode_charnames(prod_orig)


        print rule
        m= re.match('([^+]+)\+([^+]+)$',rule)
        assert m
        
        l = m.group(1) #left
        r =m.group(2)  #right

        cl_l=re.findall('(?<=<)[^<]+(?=>)',l)
        cl_r=re.findall('(?<=<)[^<]+(?=>)',r)
        onmatch_rules.append(( (cl_l, cl_r) , prod ))
    return(onmatch_rules)
    
def rules_from_yaml_data(rules_raw):
    """
    Returns sorted and usable parser rules from yaml file. 

    rules_raw is a dictionary (loaded from yaml):
        key: <previous token class> token token <next token class> 
        value: production

    previous class and next class of token are optional. 
    The production allows \N{unicode char name} strings.

    Output of return is list of rules containing:
        prev_class: previous token class [optional, will look behind prev]
        prev:       previous tokens [optional]
        tokens:     list of tokens
        next:       next token class [optional]
        next_class: next token class [option, will look ahead of next]
        production: string production

    """
    

        # load and prepare rules
    
    rules = [] # clean list of rule
#    print "rules_r is"+str(rules_raw)
    for key in rules_raw:
        if debug: print "key is "+key+" = "+rules_raw[key]
        rule = {}           #1       #2        #3

#        if debug: print "trying "+key+" in rules_from_yaml_data()"
        """
        m = re.match(r'(?:<(.+?)> )?(.+?)(?: <(.+?)>)?$', key,re.S)

        if m.group(1): rule['prev']   = m.group(1)
        rule['tokens'] = m.group(2).split(' ')
        if m.group(2)==' ':
            rule['tokens'] = [' '] # override for space ' '
        if m.group(3): rule['next']   = m.group(3)
        rule['production'] = unescape_unicode_charnames(rules_raw[key])
        """
        _  ='(?:'   
        _ +='\('
        _ +='((?:\s?<.+?>\s+)+)?'# '(?:\s?<(.+?)>\s+)?' # group 1, prev class (in brackets indicating cluster)
        _ +='(.+?)\s?' # group 2, prev tokens (to be split)
        _ +='\) '
        _ +='|' # either a cluster or a particular previous class (Could add additional support, e.g. class or paretic.
        _ +='((?:\s?<.+?>\s+)+)?' # group 3, prev class (not in cluster)
        _ +=')?'
        _ += '(.+?)' # group 4, tokens
        _ += '(?:' # cluster for following tokens, clusters 
        _ += ' \('
        _ += '\s?(.+?)' # group 5, next tokens
        _ += '((?:\s?<.+?>\s+?)+)?' # group 6, next class
        _ += '\s?\)'
        _ += '|'
        _ += ' ((?:<.+?>\s?)+)?' # group 7, follo
        _ += ')?$'
        
        m = re.match (_, key, re.S)
        assert (m is not None)
        if m.group(1): rule['prev_classes'] = re.findall('<(.+?)>',m.group(1))
        if m.group(2): rule['prev_tokens'] = m.group(2).split(' ')
        if m.group(3): rule['prev_classes'] =  re.findall('<(.+?)>',m.group(3))
        if m.group(4)==' ':
            rule['tokens'] = ' '
        else:
            rule['tokens'] = m.group(4).split(' ')
        if m.group(5): rule['next_tokens'] = m.group(5).split(' ')
        if m.group(6): rule['next_classes'] = re.findall('<(.+?)>',m.group(6))
        if m.group(7): rule['next_classes'] = re.findall('<(.+?)>',m.group(7))
            
        rule['production'] = unescape_unicode_charnames(rules_raw[key])
        if debug:print rule
        if debug:print '----'
        rules.append(rule)

    return rules

debug=False
class Parser:
    error_on_last = False
    last_string = ''
    error_string = ''

    def generate_token_match_string(self):
        tokens = self.tokens.keys()
        sorted_tokens = sorted(tokens, key=len, reverse=True)
        escaped_tokens = map(re.escape, sorted_tokens)
        tokens_re_string = '|'.join(escaped_tokens)+'|.' # grab unknowns
        return tokens_re_string

    def generate_token_match_re(self):
        '''
        Create regular expression from Parser.tokens sorted by length

        Adds final "." in case nothing found
        '''

        tokens = self.tokens.keys()
        sorted_tokens = sorted(tokens, key=len, reverse=True)
        escaped_tokens = map(re.escape, sorted_tokens)
        tokens_re_string = '|'.join(escaped_tokens)+'|.' # grab unknowns
        return re.compile(tokens_re_string, re.S)

    def tokenize(self,input):
        return self.token_match_re.findall(input)

    
    def __init__(self, yaml_file='', data=None):
        
        if data != None:
            print "You got data, son."
        elif yaml_file != '':
            data = load_yaml(yaml_file)
        else: 
            assert data is not None
        self.rules = rules_from_yaml_data(data['rules']) # specifically YAML here
        if 'onmatch' in data:
            self.onmatch_rules = onmatch_rules_from_yaml_data(data['onmatch'])
        else:
            self.onmatch_rules = False

        rules = self.rules
        rules.sort(cmp=compare_rules)
        self.tokens = data['tokens']
        self.token_match_re = self.generate_token_match_re()

if __name__ == '__main__':
    import pdb
    pdb.set_trace()  
    p = Parser('devanagari.yaml')
    pdb.set_trace()  
    print(p.parse("tah"))#rah_rau))o;n"))#taa tah tii itihaas"))
    print 'hi'
    #print_scan(s,knownOnly=False)
    #scn = scan(" ko))sab paimaane be-.sarfah jab siim-o-zar miizaan")#be-;xvudii le ga))ii kahaa;n mujh ko")#der se inti:zaar hai apnaa")# faryaadii hai kis kii sho;xii-e ta;hriir kaa")
    #print_scan(scn,knownOnly=False)

