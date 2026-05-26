import React from 'react'

export default function Dashboard() {
  return (
    <div className="min-h-screen p-6 bg-neutral-900 text-white">
      <h1 className="text-3xl mb-4">Dashboard</h1>
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 bg-gray-800 p-4 rounded">Main content / widgets</div>
        <div className="bg-gray-800 p-4 rounded">Activity feed</div>
      </div>
    </div>
  )
}
