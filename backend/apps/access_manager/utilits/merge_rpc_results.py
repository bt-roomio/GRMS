from typing import List


def merge_rpc_results(results: List[dict]) -> dict:
    """Combine per-request RPC results into one: it fails if any request failed.

    The first failed result (or the first result) supplies the remaining keys,
    and `results` keeps every individual result.
    """
    if len(results) == 1:
        return results[0]

    failed = [result for result in results if not result.get("success")]
    messages = dict.fromkeys(result.get("message", "") for result in (failed or results))
    merged = dict(failed[0] if failed else results[0]) if results else {}
    merged.update({"success": not failed, "message": "; ".join(messages), "results": results})
    return merged
