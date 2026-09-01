# MeteringDashboard component — receives data from API at port 3000
export default function MeteringDashboard() { return (
  <div className="p-6 bg-white rounded-lg shadow">
    <ul className='list-disc pl-5 space-y-2'>
      <li>Total requests this month: {data.monthlyRequests}</li>
    </ul>
  </div>
)