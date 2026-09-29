interface Props {
  page: number;
  totalPages: number;
  total: number;
  onChange: (page: number) => void;
}

export function Pagination({ page, totalPages, total, onChange }: Props) {
  return (
    <nav className="pagination" aria-label="Pagination">
      <span className="muted">{total} total · page {page} of {totalPages}</span>
      <button type="button" className="btn" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        Previous
      </button>
      <button type="button" className="btn" disabled={page >= totalPages} onClick={() => onChange(page + 1)}>
        Next
      </button>
    </nav>
  );
}
