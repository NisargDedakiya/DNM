# Phase G: Implementation Guide & Code Examples

---

## 🔧 Installation & Integration

### Step 1: Verify File Structure
```bash
webapp/
├── src/
│   ├── api/
│   │   └── clients/
│   │       ├── integrations.ts (existing)
│   │       └── bugcrowd.ts (existing)
│   ├── components/
│   │   ├── WorkingStatus.jsx ✅ NEW
│   │   ├── VulnerabilitySection.jsx ✅ NEW
│   │   ├── ManualCheck.jsx ✅ NEW
│   │   └── ReportGeneration.jsx ✅ NEW
│   ├── pages/
│   │   └── PersonalDashboard.jsx ✅ NEW
│   ├── services/
│   │   ├── websocket.js ✅ NEW
│   │   └── huntApi.js ✅ NEW
│   ├── stores/
│   │   └── authStore.ts (existing)
│   ├── client.ts (existing - Axios instance)
│   └── App.jsx or routes.tsx (existing)
```

### Step 2: Register Route
```typescript
// In webapp/src/App.jsx or routes configuration file

import PersonalDashboard from './pages/PersonalDashboard';

// Add to your route definitions:
<Route 
  path="/app/dashboard" 
  element={<PersonalDashboard />} 
/>

// Or in a routes array:
{
  path: '/app/dashboard',
  element: <PersonalDashboard />,
  name: 'Hunting Workspace'
}
```

### Step 3: Verify Environment Variables
```bash
# In .env or .env.local
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/api/ws

# For production:
VITE_API_BASE_URL=https://api.nisarghunter.com/api
VITE_WS_URL=wss://api.nisarghunter.com/api/ws
```

### Step 4: Test Application
```bash
# Start development server
cd webapp
npm run dev

# Open browser
# Navigate to http://localhost:5173/app/dashboard

# Check console for errors
# Verify WebSocket connects (should see "[WebSocket] Connected successfully")
```

---

## 📚 Code Examples

### Example 1: WebSocket Connection

```javascript
// In your app initialization
import websocket from './services/websocket';
import { useAuthStore } from './stores/authStore';

// In a component:
useEffect(() => {
  const { user, organization } = useAuthStore.getState();
  
  // Initialize WebSocket
  websocket.connect(user.token, organization.id)
    .then(() => {
      console.log('✅ WebSocket connected');
      
      // Subscribe to real-time events
      websocket.onReconFeed((data) => {
        console.log('Recon event:', data);
      });
      
      websocket.onFindingUpdate((data) => {
        console.log('Finding update:', data);
      });
    })
    .catch(err => {
      console.error('❌ WebSocket failed:', err);
    });
  
  // Cleanup
  return () => {
    websocket.disconnect();
  };
}, []);
```

### Example 2: Fetching Active Hunts

```javascript
import huntApi from './services/huntApi';
import { useAuthStore } from './stores/authStore';

export function ActiveHuntsList() {
  const [hunts, setHunts] = useState([]);
  const [loading, setLoading] = useState(true);
  const { organization } = useAuthStore();
  
  useEffect(() => {
    const loadHunts = async () => {
      try {
        const data = await huntApi.getActiveHunts(organization.id);
        setHunts(data);
      } catch (err) {
        console.error('Failed to load hunts:', err);
      } finally {
        setLoading(false);
      }
    };
    
    loadHunts();
  }, [organization.id]);
  
  if (loading) return <div>Loading hunts...</div>;
  
  return (
    <div>
      {hunts.map(hunt => (
        <div key={hunt.id}>
          <h3>{hunt.name}</h3>
          <p>Status: {hunt.status}</p>
        </div>
      ))}
    </div>
  );
}
```

### Example 3: Handling Real-time Finding Updates

```javascript
export function FindingsUpdater() {
  const [findings, setFindings] = useState([]);
  
  useEffect(() => {
    // Subscribe to finding updates
    const unsubscribe = websocket.onFindingUpdate((data) => {
      const { finding_id, update, organization_id } = data;
      
      // Only update if for current organization
      if (organization_id === getCurrentOrgId()) {
        setFindings(prev => {
          // Update existing finding or add new one
          const updated = prev.map(f => 
            f.id === finding_id ? { ...f, ...update } : f
          );
          
          // Add new finding if not found
          if (!prev.find(f => f.id === finding_id)) {
            updated.push({ id: finding_id, ...update });
          }
          
          return updated;
        });
      }
    });
    
    return unsubscribe;
  }, []);
  
  return <VulnerabilitySection findings={findings} />;
}
```

### Example 4: Submitting Verification

```javascript
async function handleVerifyFinding(findingId, verificationData) {
  try {
    // Submit verification
    const result = await huntApi.submitVerification(findingId, {
      checklist: ['access', 'reproduce', 'impact'],
      evidence: 'Screenshot showing SQL injection...',
      exploitation: {
        notes: 'Can read all user data from database',
        reproduction_steps: '1. Go to /search\n2. Enter: \' OR \'1\'=\'1'
      },
      verified: true
    });
    
    console.log('✅ Verification submitted:', result);
    
    // Status should update via WebSocket
    // If not, you can manually update:
    // setFindings(prev => prev.map(f => 
    //   f.id === findingId 
    //     ? { ...f, status: 'verified' } 
    //     : f
    // ));
    
  } catch (error) {
    console.error('❌ Verification failed:', error);
    showError('Failed to submit verification');
  }
}
```

### Example 5: Generating a Report

```javascript
async function handleGenerateReport(findingId, format = 'hackerone') {
  try {
    // Get report preview first
    const preview = await huntApi.getReportPreview(findingId, format);
    console.log('Report preview:', preview);
    
    // If good, generate full report
    const report = await huntApi.generateReport(findingId, {
      severity: 'high',
      format: format
    });
    
    console.log('✅ Report generated');
    console.log('Quality score:', report.quality_score);
    console.log('Report text:', report.report);
    
    // Export report
    const blob = await huntApi.exportReport(report.id, 'markdown');
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report_${findingId}.md`;
    a.click();
    
  } catch (error) {
    console.error('❌ Report generation failed:', error);
  }
}
```

### Example 6: Using Components Independently

```javascript
// Import individual components
import WorkingStatus from './components/WorkingStatus';
import VulnerabilitySection from './components/VulnerabilitySection';
import ManualCheck from './components/ManualCheck';

export function MyCustomDashboard() {
  const [selectedFinding, setSelectedFinding] = useState(null);
  const [showVerify, setShowVerify] = useState(false);
  const { organization } = useAuthStore();
  
  return (
    <div className="grid grid-cols-2 gap-6">
      {/* Left: Working Status */}
      <WorkingStatus 
        huntId="hunt-123" 
        organizationId={organization.id}
      />
      
      {/* Right: Vulnerabilities */}
      <VulnerabilitySection
        organizationId={organization.id}
        onSelectFinding={setSelectedFinding}
      />
      
      {/* Modal: Manual Check */}
      {showVerify && selectedFinding && (
        <ManualCheck
          finding={selectedFinding}
          onClose={() => setShowVerify(false)}
          onVerified={(findingId) => {
            console.log('Verified:', findingId);
            setShowVerify(false);
          }}
        />
      )}
    </div>
  );
}
```

---

## 🎯 Common Patterns

### Pattern 1: Organization-Aware Component

```javascript
import { useAuthStore } from './stores/authStore';

export function OrganizationAwareComponent() {
  const { organization, user } = useAuthStore();
  
  // Verify we have organization context
  if (!organization?.id) {
    return <div>No organization selected</div>;
  }
  
  // Use organization.id for all API calls
  useEffect(() => {
    loadDataForOrganization(organization.id);
  }, [organization.id]);
  
  return <div>Organization: {organization.name}</div>;
}
```

### Pattern 2: Real-time State Management

```javascript
export function RealtimeComponent() {
  const [data, setData] = useState([]);
  
  useEffect(() => {
    // Load initial data
    loadInitialData();
    
    // Subscribe to real-time updates
    const unsubscribe = websocket.onEvent((update) => {
      setData(prev => updateDataWithRealtime(prev, update));
    });
    
    // Cleanup subscription
    return unsubscribe;
  }, []);
  
  return <DataDisplay data={data} />;
}
```

### Pattern 3: Modal Workflow

```javascript
export function ModalWorkflowComponent() {
  const [showModal, setShowModal] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  
  const handleOpen = (item) => {
    setSelectedItem(item);
    setShowModal(true);
  };
  
  const handleClose = () => {
    setShowModal(false);
    setSelectedItem(null);
  };
  
  const handleComplete = (itemId) => {
    console.log('Completed:', itemId);
    handleClose();
    // Update UI
  };
  
  return (
    <>
      <button onClick={() => handleOpen(item)}>Open Modal</button>
      
      {showModal && selectedItem && (
        <YourModal
          data={selectedItem}
          onClose={handleClose}
          onComplete={handleComplete}
        />
      )}
    </>
  );
}
```

### Pattern 4: Error Handling

```javascript
async function handleAsyncOperation() {
  try {
    setLoading(true);
    setError(null);
    
    const result = await huntApi.someOperation();
    
    if (!result.success) {
      throw new Error(result.message);
    }
    
    setData(result);
    showSuccess('Operation completed');
    
  } catch (err) {
    console.error('Operation failed:', err);
    setError(err.message);
    showError(`Failed: ${err.message}`);
    
  } finally {
    setLoading(false);
  }
}
```

### Pattern 5: Filter & Search

```javascript
export function FilteredList({ items }) {
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  
  const filtered = items
    .filter(item => {
      if (filter !== 'all' && item.type !== filter) return false;
      if (search && !item.name.includes(search)) return false;
      return true;
    })
    .sort((a, b) => b.priority - a.priority);
  
  return (
    <>
      <input
        type="text"
        placeholder="Search..."
        value={search}
        onChange={e => setSearch(e.target.value)}
      />
      
      <select value={filter} onChange={e => setFilter(e.target.value)}>
        <option value="all">All</option>
        <option value="high">High</option>
        <option value="low">Low</option>
      </select>
      
      <div>
        {filtered.map(item => (
          <div key={item.id}>{item.name}</div>
        ))}
      </div>
    </>
  );
}
```

---

## 🧪 Testing Examples

### Test 1: WebSocket Connection

```javascript
describe('WebSocket Service', () => {
  it('should connect successfully', async () => {
    const service = new WebSocketService();
    
    await service.connect('test-token', 'test-org');
    
    expect(service.isConnected).toBe(true);
    expect(service.getStatus().isConnected).toBe(true);
  });
  
  it('should handle reconnection', async () => {
    const service = new WebSocketService();
    const connectSpy = jest.spyOn(service, 'connect');
    
    service.ws.close();
    
    await new Promise(resolve => setTimeout(resolve, 4000));
    
    expect(connectSpy).toHaveBeenCalled();
  });
});
```

### Test 2: API Methods

```javascript
describe('Hunt API', () => {
  it('should fetch active hunts', async () => {
    const hunts = await huntApi.getActiveHunts('org-123');
    
    expect(Array.isArray(hunts)).toBe(true);
    expect(hunts[0]).toHaveProperty('id');
    expect(hunts[0]).toHaveProperty('name');
  });
  
  it('should filter findings by severity', async () => {
    const critical = await huntApi.getCriticalFindings('org-123', {
      severity: 'critical'
    });
    
    expect(critical.every(f => f.severity === 'critical')).toBe(true);
  });
});
```

### Test 3: Component Rendering

```javascript
describe('VulnerabilitySection', () => {
  it('should render findings list', () => {
    const { getByText } = render(
      <VulnerabilitySection 
        organizationId="org-123"
        onSelectFinding={jest.fn()}
      />
    );
    
    expect(getByText(/findings/i)).toBeInTheDocument();
  });
  
  it('should filter by severity', async () => {
    const { getByValue } = render(
      <VulnerabilitySection 
        organizationId="org-123"
        onSelectFinding={jest.fn()}
      />
    );
    
    const select = getByValue('all');
    fireEvent.change(select, { target: { value: 'critical' } });
    
    await waitFor(() => {
      expect(select.value).toBe('critical');
    });
  });
});
```

---

## 🔐 Security Best Practices

### ✅ DO

```javascript
// ✅ Always include organization_id
await huntApi.getFindings(organizationId);

// ✅ Use HTTPS/WSS in production
VITE_WS_URL=wss://api.nisarghunter.com

// ✅ Check permissions before showing UI
if (hasPermission('MANAGE_FINDINGS')) {
  return <VerifyButton />;
}

// ✅ Sanitize user input
<div>{sanitizeHTML(finding.description)}</div>

// ✅ Handle authentication errors
catch (err) {
  if (err.status === 401) {
    redirectToLogin();
  }
}
```

### ❌ DON'T

```javascript
// ❌ Don't hardcode organization IDs
const findings = await huntApi.getFindings('hardcoded-org-id');

// ❌ Don't use HTTP in production
VITE_WS_URL=ws://api.nisarghunter.com // ❌

// ❌ Don't show unauthorized UI
return <VerifyButton />; // No permission check

// ❌ Don't render unescaped HTML
<div dangerouslySetInnerHTML={{__html: finding.description}} />

// ❌ Don't ignore auth errors
.catch(err => {
  console.log('Error'); // Silently fails
})
```

---

## 📊 Performance Tips

### Optimize Rendering

```javascript
// Use React.memo for expensive components
const MemoizedFinding = React.memo(FindingCard, (prev, next) => {
  return prev.finding.id === next.finding.id &&
         prev.finding.status === next.finding.status;
});

// Use useCallback for handlers
const handleSelectFinding = useCallback((finding) => {
  setSelected(finding);
}, []);

// Use useMemo for computed values
const filteredFindings = useMemo(() => {
  return findings.filter(f => f.severity === severity);
}, [findings, severity]);
```

### Optimize API Calls

```javascript
// Load data in parallel
const [hunts, findings, metrics] = await Promise.all([
  huntApi.getActiveHunts(orgId),
  huntApi.getCriticalFindings(orgId),
  huntApi.getDashboardMetrics(orgId)
]);

// Limit WebSocket subscriptions
const unsubFinding = websocket.onFindingUpdate(handler);
const unsubHunt = websocket.onHuntProgress(handler);

// Return cleanup
return () => {
  unsubFinding();
  unsubHunt();
};
```

---

## 🚀 Deployment Checklist

```
Pre-Deployment:
- [ ] All 7 files in correct locations
- [ ] Routes registered
- [ ] Environment variables set
- [ ] No console errors
- [ ] WebSocket connects
- [ ] API calls work
- [ ] Modals open/close
- [ ] No memory leaks
- [ ] Mobile responsive
- [ ] Performance acceptable

Deployment:
- [ ] Build succeeds (npm run build)
- [ ] No build warnings
- [ ] Production env vars configured
- [ ] Deploy dist/ folder
- [ ] Test in staging
- [ ] Verify WebSocket URL (WSS)
- [ ] Monitor errors
- [ ] Check performance
- [ ] Validate security
- [ ] Document changes

Post-Deployment:
- [ ] Monitor uptime
- [ ] Check error logs
- [ ] Verify real-time updates
- [ ] Test all features
- [ ] Gather user feedback
- [ ] Plan improvements
```

---

## 📞 Troubleshooting Reference

| Problem | Debug | Solution |
|---------|-------|----------|
| WebSocket won't connect | Check console for errors | Verify URL, check backend running |
| Findings not showing | Check API response | Verify organization_id correct |
| Modal won't close | Check state logic | Verify onClose callback called |
| Slow performance | Check DevTools | Implement pagination, optimize queries |
| CORS errors | Check network tab | Update CORS settings in backend |
| Memory leak | Check DevTools memory | Ensure cleanup functions called |
| Token expired | Check auth store | Implement token refresh logic |
| Real-time not updating | Check WebSocket status | Verify subscription active |

---

## 🎓 Learning Resources

### Internal
- [Phase G Frontend Workspace](./PHASE_G_FRONTEND_WORKSPACE.md) - Full documentation
- [Phase G Quick Reference](./PHASE_G_QUICK_REFERENCE.md) - Quick lookup
- [API Client Documentation](../webapp/src/services/huntApi.js) - Inline docs

### External
- React Docs: https://react.dev
- WebSocket API: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
- TailwindCSS: https://tailwindcss.com/docs
- Axios: https://axios-http.com/docs/intro

---

**Implementation Guide Complete** ✅

Ready to integrate Phase G into your NisargHunter AI platform!
