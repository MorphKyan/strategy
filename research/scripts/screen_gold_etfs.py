from etf_screening_common import ScreeningSpec, build_base_parser, classify_gold, run_screening


def main() -> int:
    parser = build_base_parser("Screen gold ETFs from finshare.")
    parser.add_argument("--min-history-years", type=float, default=5.0, help="Minimum required NAV history in years.")
    args = parser.parse_args()

    spec = ScreeningSpec(
        name="Gold ETF Screening",
        slug="gold_etfs",
        description="Find gold ETFs with at least 5 years of history from finshare.",
        min_history_years=float(args.min_history_years),
        max_management_fee=None,
        classifier=classify_gold,
    )
    run_screening(spec, limit=args.limit, sleep_seconds=args.sleep_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
