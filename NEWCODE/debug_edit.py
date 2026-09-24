import appy
from appy import app, Usuario

with app.test_client() as client:
    u = Usuario.query.first()
    if not u:
        print('NO_USER')
    else:
        response = client.get(f'/usuarios/{u.id}/editar')
        print('status', response.status_code)
        print(response.get_data(as_text=True)[:4000])
