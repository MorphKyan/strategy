from etf_screening_common import ScreeningSpec, build_base_parser, classify_bond, run_screening


def main() -> int:
    parser = build_base_parser("Screen long-duration bond ETFs from finshare.")
    parser.add_argument("--min-history-years", type=float, default=5.0, help="Minimum required NAV history in years.")
    parser.add_argument("--max-management-fee", type=float, default=0.3, help="Maximum annual management fee percentage.")
    args = parser.parse_args()

    spec = ScreeningSpec(
        name="Long-Duration Bond ETF Screening",
        slug="bond_etfs",
        description="Find bond ETFs with at least 5 years of history, duration of at least 10 years, and management fee below 0.3%.",
        min_history_years=float(args.min_history_years),
        max_management_fee=float(args.max_management_fee),
        classifier=classify_bond,
    )
    run_screening(spec, limit=args.limit, sleep_seconds=args.sleep_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
