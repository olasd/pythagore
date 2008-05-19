def to_unicode (txt, pray_enc_is="ISO8859-15"):
    if isinstance(txt, unicode):
        return txt
    else:
        try:
            # We suppose the text is UTF-8
            return txt.decode("UTF-8")
        except UnicodeDecodeError:
            # else we assume (hope ?) it is pray_enc_is
            try:
                return txt.decode(pray_enc_is)
            except UnicodeDecodeError:
                # We don't know what to do, so we go for a failproof solution
                print repr(txt), " <- decoding failed with enc:%s" % pray_enc_is
                return repr(txt).decode()

e_ = to_unicode
