import SchemeRow from "@/components/SchemeRow";
import type { AreaAccount, EvidenceRecord } from "@/lib/area-account";

function groupByScheme(records: EvidenceRecord[]): Map<string, EvidenceRecord[]> {
  const groups = new Map<string, EvidenceRecord[]>();
  for (const record of records) {
    groups.set(record.scheme, [...(groups.get(record.scheme) ?? []), record]);
  }
  return groups;
}

function actionHref(
  scheme: string,
  pin: string | undefined,
  district: string,
  state: string,
): string {
  const params = new URLSearchParams({ issue: scheme });
  if (pin) params.set("pin", pin);
  else {
    params.set("district", district);
    params.set("state", state);
  }
  return `/?${params.toString()}#action`;
}

function RecordList({
  records,
  pin,
  district,
  state,
}: {
  records: EvidenceRecord[];
  pin?: string;
  district: string;
  state: string;
}) {
  return [...groupByScheme(records)].map(([scheme, schemeRecords]) => (
    <SchemeRow
      key={scheme}
      scheme={scheme}
      records={schemeRecords}
      actionHref={actionHref(scheme, pin, district, state)}
    />
  ));
}

export default function SchemeDataSection({
  account,
  pin,
  district,
  state,
}: {
  account: AreaAccount;
  pin?: string;
  district: string;
  state: string;
}) {
  const districtSchemeCount = groupByScheme(account.districtRecords).size;
  const limitCount = 3 + Number(account.missingDistrictSchemes.length > 0);

  return (
    <>
      <section id="evidence" className="account-section" aria-labelledby="district-records-heading">
        <header className="account-section__header">
          <h2 id="district-records-heading">What district records report</h2>
          <p>
            {districtSchemeCount} {districtSchemeCount === 1 ? "service has" : "services have"} records.
            Open one for its figures, dates, and source.
          </p>
        </header>
        {account.districtRecords.length > 0 ? (
          <div className="ledger">
            <RecordList records={account.districtRecords} pin={pin} district={district} state={state} />
          </div>
        ) : (
          <p className="coverage-empty">
            Hisaab has no district-grain scheme record for this area. That does
            not mean no money was allocated or no service was delivered.
          </p>
        )}
      </section>

      {account.stateRecords.length > 0 && (
        <section className="account-section account-section--state" aria-labelledby="state-context-heading">
          <details className="state-context">
            <summary>
              <span>
                <strong id="state-context-heading">State context ({account.stateRecords.length})</strong>
                <small>These records describe the state, not this district.</small>
              </span>
            </summary>
            <div className="state-context__body">
              <div className="ledger ledger--state">
                <RecordList records={account.stateRecords} pin={pin} district={district} state={state} />
              </div>
            </div>
          </details>
        </section>
      )}

      <section className="account-section" aria-labelledby="coverage-heading">
        <details className="coverage-limits text-disclosure">
          <summary id="coverage-heading">Data Hisaab does not have ({limitCount})</summary>
          <div className="coverage-limits__body">
            <ul>
              <li>District finance is not published in the sources Hisaab uses for PMAY-G, PM Kisan, JJM, PM POSHAN, PDS/NFSA, or SBM-G. Separate state records may appear above when available.</li>
              <li>NSAP district records show beneficiary counts for their source month. Hisaab omits the annualized central-share estimate because it is imputed rather than reported district spending.</li>
              <li>UDISE+ education records in Hisaab are state-level only.</li>
              {account.missingDistrictSchemes.length > 0 && (
                <li>
                  No district-grain record was found in Hisaab for: {account.missingDistrictSchemes.join(", ")}.
                  This is a data-coverage gap, not evidence of no activity.
                </li>
              )}
            </ul>
          </div>
        </details>
      </section>
    </>
  );
}
