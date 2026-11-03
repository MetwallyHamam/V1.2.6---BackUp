import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { AuthProvider } from '../auth/AuthContext'
import { ProtectedRoute } from '../routes/ProtectedRoute'

function LoginDestination(){const location=useLocation();const from=(location.state as {from?:{pathname?:string;search?:string}}|null)?.from;return <div>Login destination {from?.pathname}{from?.search}</div>}

test('redirects anonymous users to login and preserves their destination', () => {
  render(<MemoryRouter initialEntries={['/private?ticket=42']}><AuthProvider><Routes>
    <Route path="/login" element={<LoginDestination/>} />
    <Route element={<ProtectedRoute />}><Route path="/private" element={<div>Private</div>} /></Route>
  </Routes></AuthProvider></MemoryRouter>)
  expect(screen.getByText('Login destination /private?ticket=42')).toBeInTheDocument()
})
