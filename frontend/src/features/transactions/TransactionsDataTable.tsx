import type { TransactionRecord } from '../../shared/types/api'
import { formatNumber } from './transactionsUtils'

type TransactionsDataTableProps = {
  loading: boolean
  rows: TransactionRecord[]
}

export function TransactionsDataTable({ loading, rows }: TransactionsDataTableProps) {
  if (loading) {
    return <p>Loading transactions...</p>
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Account</th>
          <th>ISIN</th>
          <th>Name</th>
          <th>Type</th>
          <th>Quantity</th>
          <th>Settle Amount</th>
          <th>Settle Curr</th>
          <th>FX Rate</th>
          <th>Amount EUR</th>
          <th>Internal ID</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={`${row.internal_id ?? row.isin ?? 'row'}-${index}`}>
            <td>{row.trade_date ?? '-'}</td>
            <td>{row.account ?? '-'}</td>
            <td>{row.isin ?? '-'}</td>
            <td>{row.name ?? '-'}</td>
            <td>{row.transaction_type ?? '-'}</td>
            <td>{formatNumber(row.quantity, 4)}</td>
            <td>{formatNumber(row.settle_amount, 2)}</td>
            <td>{row.settle_currency ?? '-'}</td>
            <td>{formatNumber(row.fx_rate, 6)}</td>
            <td>{formatNumber(row.amount_eur, 2)}</td>
            <td>{row.internal_id ?? '-'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
