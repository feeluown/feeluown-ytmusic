import re


def patch_pytube():
    """patch pytube so that it can get stream url.

    In Pytube version 15.0.0, you just need to remove ; in line 287 of cipher.py file.
    Check https://stackoverflow.com/a/76643802/4302892 for details.
    """

    from pytube.exceptions import RegexMatchError
    from pytube import cipher

    logger = cipher.logger

    def get_throttling_function_name(js: str) -> str:
        """Extract the name of the function that computes the throttling parameter.

        :param str js:
            The contents of the base.js asset file.
        :rtype: str
        :returns:
            The name of the function used to compute the throttling parameter.
        """
        function_patterns = [
            # https://github.com/ytdl-org/youtube-dl/issues/29326#issuecomment-865985377
            # https://github.com/yt-dlp/yt-dlp/commit/48416bc4a8f1d5ff07d5977659cb8ece7640dcd8
            # var Bpa = [iha];
            # ...
            # a.C && (b = a.get("n")) && (b = Bpa[0](b), a.set("n", b),
            # Bpa.length || iha("")) }};
            # In the above case, `iha` is the relevant function name
            r'a\.[a-zA-Z]\s*&&\s*\([a-z]\s*=\s*a\.get\("n"\)\)\s*&&\s*'
            r'\([a-z]\s*=\s*([a-zA-Z0-9$]+)(\[\d+\])?\([a-z]\)',
        ]
        logger.debug('Finding throttling function name')
        for pattern in function_patterns:
            regex = re.compile(pattern)
            function_match = regex.search(js)
            if function_match:
                logger.debug("finished regex search, matched: %s", pattern)
                if len(function_match.groups()) == 1:
                    return function_match.group(1)
                idx = function_match.group(2)
                if idx:
                    idx = idx.strip("[]")
                    array = re.search(
                        r'var {nfunc}\s*=\s*(\[.+?\])'.format(
                            nfunc=re.escape(function_match.group(1))),
                        js
                    )
                    if array:
                        array = array.group(1).strip("[]").split(",")
                        array = [x.strip() for x in array]
                        return array[int(idx)]

        raise RegexMatchError(
            caller="get_throttling_function_name", pattern="multiple"
        )

    cipher.get_throttling_function_name = get_throttling_function_name
