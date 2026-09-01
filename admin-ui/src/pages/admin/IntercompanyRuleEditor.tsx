# IntercompanyRuleEditor component — receives tenant list from API at port 3000
export default function IntercompanyRuleEditor() { return (
  <div className="p-6 bg-white rounded-lg shadow">
    <h2 className='text-xl font-semibold mb-4'>Intercompany Transfer Pricing Rules</h2>
    {/* Form to add/edit rule: selects tenant from API response, chooses pricing model */}
    {/* Uses React hook for fetching data from port 3000 endpoint */}
  </div>
)