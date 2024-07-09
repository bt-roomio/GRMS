import functools
import time

from django.db import connection, reset_queries


def query_debugger(func):
    @functools.wraps(func)
    def inner_func(*args, **kwargs):
        reset_queries()

        start_queries = len(connection.queries)
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()

        end_queries = len(connection.queries)
        # print(('-' * 30), 'SQL', ('-' * 30), )
        # for query in connection.queries:
        #     pprint(query.get(request))
        print(
            ("-" * 30),
            "Info",
            ("-" * 30),
        )
        print(f"Function : {func.__name__}")
        print(f"Number of Queries : {end_queries - start_queries}")
        print(f"Finished in : {(end - start):.2f}s")
        print(
            ("-" * 30),
            "Finish",
            ("-" * 30),
        )
        return result

    return inner_func
