import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";

const Register: React.FC = () => {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const register = useAuthStore((s) => s.register);
  const loading = useAuthStore((s) => s.loading);
  const navigate = useNavigate();

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await register(username, email, password);
      navigate("/login");
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || "Registration failed");
    }
  };

  return (
    <div className="max-w-md mx-auto mt-20 bg-white p-6 rounded shadow">
      <h1 className="text-2xl mb-4">Register</h1>
      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" className="p-2 border" />
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" className="p-2 border" />
        <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="Password" className="p-2 border" />
        {error && <div className="text-red-500">{error}</div>}
        <button disabled={loading} className="bg-green-600 text-white px-4 py-2 rounded">{loading ? 'Registering...' : 'Register'}</button>
      </form>
    </div>
  );
};

export default Register;
