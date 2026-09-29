/** Correlation matrix as a labelled table; every cell shows its number, shade is secondary. */
export function CorrelationTable({ labels, matrix }: { labels: string[]; matrix: (number | null)[][] }) {
  if (labels.length === 0) return <p className="muted">Correlation data is not available.</p>;
  return (
    <div className="table-wrap">
      <table>
        <caption>Pearson correlations between numeric variables (−1 to 1)</caption>
        <thead>
          <tr>
            <td />
            {labels.map((label) => <th key={label} scope="col">{label}</th>)}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={labels[i]}>
              <th scope="row">{labels[i]}</th>
              {row.map((value, j) => (
                <td
                  key={labels[j]}
                  className="corr-cell"
                  style={value === null ? undefined : { background: `color-mix(in srgb, var(--series-1) ${Math.round(Math.abs(value) * 45)}%, transparent)` }}
                >
                  {value === null ? "n/a" : value.toFixed(2)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
