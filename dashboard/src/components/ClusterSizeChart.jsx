import { BarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, LabelList } from 'recharts';
import { number, axisNumber } from '../services/formatNumbers.js';

export default function ClusterSizeChart({ profiles }) {
  return <><div className="chart-unit">Đơn vị: người dùng</div><div className="chart-frame">
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={profiles} margin={{ top: 28, right: 16, left: 0, bottom: 8 }} accessibilityLayer>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" /><YAxis tickFormatter={axisNumber} width={70} allowDecimals={false} />
        <Tooltip formatter={value => [`${number(value)} người dùng`, 'Kích thước cụm']} />
        <Bar dataKey="userCount" fill="#3865b5" isAnimationActive={false} radius={[4, 4, 0, 0]}>
          <LabelList dataKey="userCount" position="top" formatter={number} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  </div></>;
}
