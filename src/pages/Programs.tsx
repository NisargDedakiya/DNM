import React, { useEffect, useState } from "react";
import api from "../api/client";

const Programs: React.FC = () => {
  const [programs, setPrograms] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [platform, setPlatform] = useState("");
  const [scope, setScope] = useState("");

  const fetch = async () => {
    try {
      const r = await api.get("/programs");
      setPrograms(r.data || []);
    } catch (e) {
      // ignore
    }
  };

  useEffect(() => { fetch(); }, []);

  const create = async () => {
    try {
      await api.post("/programs", { name, platform, scope });
      setName(""); setPlatform(""); setScope("");
      fetch();
    } catch (e) {
      // ignore
    }
  };

  const remove = async (id: string) => {
    try {
      await api.delete(`/programs/${id}`);
      fetch();
    } catch (e) {}
  };

  return (
    <div>
      <h1 className="text-2xl mb-4">Programs</h1>
      <div className="mb-4 p-4 bg-white rounded shadow">
        <h3>Create program</h3>
        <input className="border p-2 w-full mb-2" placeholder="Name" value={name} onChange={(e)=>setName(e.target.value)} />
        <input className="border p-2 w-full mb-2" placeholder="Platform" value={platform} onChange={(e)=>setPlatform(e.target.value)} />
        <textarea className="border p-2 w-full mb-2" placeholder="Scope" value={scope} onChange={(e)=>setScope(e.target.value)} />
        <button onClick={create} className="bg-blue-600 text-white px-3 py-1 rounded">Create</button>
      </div>

      <ul className="space-y-2">
        {programs.map(p => (
          <li key={p.id} className="p-3 bg-white rounded shadow flex justify-between items-center">
            <div>
              <div className="font-semibold">{p.name}</div>
              <div className="text-sm text-gray-600">{p.platform}</div>
            </div>
            <div>
              <button onClick={()=>remove(p.id)} className="text-red-500">Delete</button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default Programs;
