"""Run meaningful stage-1 checks before using the generated data."""

from dataclasses import replace
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from archive.calibrate import choose_count
from calculations.simulate import Settings, generate, maximum_drawdown, run, simulate_batch


def collected(settings, count, model):
    results = list(generate(settings, count, 32, 123, model))
    return np.concatenate([batch[0] for _, batch in results])


def main():
    # A shared final value does not imply a shared maximum drawdown.
    paths = np.array([[100, 90, 110, 100], [100, 110, 90, 100]], dtype=float)
    np.testing.assert_allclose(maximum_drawdown(paths), [0.10, 20 / 110])
    np.testing.assert_array_equal(maximum_drawdown(np.array([[100, 110, 120]])), [0])

    settings = Settings(assets=4, days=20)
    flat = replace(settings, normal_log_mean=0, normal_log_vol=0)
    values, drawdowns, days = simulate_batch(flat, 12, 5, "normal")
    np.testing.assert_allclose(values, flat.initial_value)
    np.testing.assert_array_equal(drawdowns, 0)
    np.testing.assert_array_equal(days, 0)

    # With transitions disabled, both models must give identical paths.
    no_crisis = replace(settings, enter_crisis_probability=0)
    np.testing.assert_array_equal(collected(no_crisis, 97, "normal"),
                                  collected(no_crisis, 97, "crisis"))
    np.testing.assert_array_equal(collected(settings, 97, "crisis"),
                                  collected(settings, 97, "crisis"))

    # Batch completion order must not affect the assembled paths.
    ordered = collected(settings, 97, "crisis")
    reordered = np.empty_like(ordered)
    for start, (values, _, _) in reversed(list(generate(settings, 97, 32, 123, "crisis"))):
        reordered[start:start + len(values)] = values
    np.testing.assert_array_equal(ordered, reordered)
    assert np.all(ordered > 0)
    assert np.all((maximum_drawdown(ordered) >= 0)
                  & (maximum_drawdown(ordered) < 1))
    all_crisis = replace(settings, enter_crisis_probability=1,
                         leave_crisis_probability=0)
    _, _, days = simulate_batch(all_crisis, 12, 5, "crisis")
    np.testing.assert_array_equal(days, settings.days)

    # Saved binary arrays must match the actual generated results, including
    # the partial final batch; summaries must match independently sorted values.
    with TemporaryDirectory() as temporary:
        output = Path(temporary)
        with redirect_stdout(StringIO()):
            summary = run(settings, 97, 32, 123, "crisis", output)
        saved = np.load(output / "crisis_drawdowns.npy", allow_pickle=False)
        np.testing.assert_array_equal(saved, maximum_drawdown(ordered))
        np.testing.assert_array_equal(np.load(output / "crisis_final_values.npy"), ordered[:, -1])
        np.testing.assert_allclose(summary["drawdown_99th_percentile"], np.quantile(saved, 0.99))
        np.testing.assert_allclose(summary["mean_drawdown_worst_one_percent"], np.sort(saved)[-1])
        assert np.load(output / "crisis_crisis_days.npy").dtype == np.int32
        try:
            run(settings, 97, 32, 123, "crisis", output)
        except FileExistsError:
            pass
        else:
            raise AssertionError("Existing output was not protected.")

    assert choose_count(0.00005, 900, 4096, 100_000_000) % 4096 == 0
    assert choose_count(0.00005, 900, 4096, 100_000_000) * 0.00005 >= 900
    try:
        choose_count(0.0000001, 900, 4096, 100_000_000)
    except ValueError:
        pass
    else:
        raise AssertionError("Oversized production plan was not rejected.")
    print("PASS: hand-calculated drawdowns, flat market, disabled crises, repeatability,")
    print("batch ordering, forced crises, positive values, drawdown bounds, binary outputs,")
    print("tail summaries, output protection, and production-size selection.")
    print("Still required: analytical normal-return benchmark and parallel equivalence tests.")


if __name__ == "__main__":
    main()
