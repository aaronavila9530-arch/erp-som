(() => {
  'use strict';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let instance;
  class Admin {
    constructor(root, config) { this.root=root;this.config=config;this.tab='create';this.dirty=false;this.disposed=false;this.target='';this.sequence=0;this.offset=0; }
    canLeave() { return !this.busy && (!this.dirty || confirm('Hay cambios sin guardar. Desea descartarlos?')); }
    destroy() { this.disposed=true;this.root.querySelector('form')?.reset(); }
    message(text, error=false) { if(this.disposed)return;const el=this.root.querySelector('[data-message]');if(el){el.textContent=text;el.classList.toggle('error',error);} }
    async start() {
      this.root.innerHTML='<section class="som-admin"><h2>Usuarios y permisos</h2><p>Acceso administrativo</p><button data-authorize>Autorizar acceso</button><p data-message role="status"></p></section>';
      this.root.querySelector('[data-authorize]').onclick=()=>this.load();
    }
    async load() {
      if(!this.canLeave())return;
      this.message('Cargando...');
      try {
        const meta=await this.config.request('/admin/users/meta');
        const people=await this.config.request('/admin/users/people');
        const users=await this.config.request('/admin/users');
        if(this.disposed)return;
        this.meta=meta;this.people=people.people||[];this.users=users.users||[];this.dirty=false;this.render();
        if(this.tab==='permissions' && this.target)await this.permissions();
        if(this.tab==='audit')await this.audit();
      } catch(error) { this.message(error.message,true); }
    }
    matrix(values={}) {
      return `<div class="admin-matrix">${this.meta.modules.map(module=>`<fieldset><legend>${esc(module.label)}</legend><div class="admin-permission-grid">${(this.meta.module_actions[module.code]||this.meta.actions).map(action=>`<label><input type="checkbox" data-module="${esc(module.code)}" data-permission="${esc(action.code)}" ${(values[module.code]||[]).includes(action.code)?'checked':''}>${esc(action.label)}</label>`).join('')}</div></fieldset>`).join('')}</div>`;
    }
    selectedPermissions() {
      const result={};this.root.querySelectorAll('[data-permission]:checked').forEach(el=>{(result[el.dataset.module]??=[]).push(el.dataset.permission);});return result;
    }
    watch() { this.root.querySelectorAll('form input,form select,[data-permission]').forEach(el=>el.addEventListener('change',()=>{this.dirty=true;})); }
    render() {
      const active=this.users.filter(u=>u.activo).length;
      this.root.innerHTML=`<section class="som-admin"><header><div><small>ADMIN / USUARIOS GLOBALES</small><h2>Usuarios y permisos</h2></div><button class="secondary" data-reload>Recargar</button></header>
      <div class="admin-metrics"><div><span>Usuarios</span><strong>${this.users.length}</strong></div><div><span>Activos</span><strong>${active}</strong></div><div><span>Inactivos</span><strong>${this.users.length-active}</strong></div></div>
      <nav role="tablist" aria-label="Administracion">${[['create','Crear usuario'],['permissions','Permisos'],['audit','Auditoria']].map(([id,label])=>`<button role="tab" aria-selected="${id===this.tab}" data-tab="${id}">${label}</button>`).join('')}</nav><p data-message role="status" aria-live="polite"></p><div data-panel></div></section>`;
      this.root.querySelector('[data-reload]').onclick=()=>this.load();
      this.root.querySelectorAll('[data-tab]').forEach(el=>el.onclick=async()=>{if(!this.canLeave())return;this.dirty=false;this.sequence++;this.tab=el.dataset.tab;this.render();if(this.tab==='permissions'&&this.target)await this.permissions();if(this.tab==='audit')await this.audit();});
      const panel=this.root.querySelector('[data-panel]');
      if(this.tab==='create') {
        panel.innerHTML=`<form data-create><div class="admin-form"><label>Persona base<select name="person"><option value="">Seleccione empleado o proveedor</option>${this.people.map((p,i)=>`<option value="${i}">${esc(p.source_type)}: ${esc(p.label)}${p.usuario?' ('+esc(p.usuario)+')':''}</option>`).join('')}</select></label><label>Usuario<input name="usuario" autocomplete="off" pattern="[a-zA-Z0-9._-]{4,40}" minlength="4" maxlength="40" required></label><label>Contrasena temporal<input name="password" type="password" autocomplete="new-password" minlength="12" maxlength="72" required></label><label>Rol base<select name="rol">${this.meta.roles.map(role=>`<option value="${esc(role)}">${esc(role)}</option>`).join('')}</select></label><label class="admin-check"><input name="activo" type="checkbox" checked>Activo</label></div>
          <ul class="admin-rules">${this.meta.password_rules.map(rule=>`<li>${esc(rule)}</li>`).join('')}</ul><h3>Permisos iniciales</h3><p class="admin-notice">Sin permisos marcados se aplican los permisos heredados del rol. Los roles admin y master tienen privilegios administrativos.</p>${this.matrix()}<div class="admin-save"><button type="submit">Crear usuario</button></div></form>`;
        const form=panel.querySelector('form');
        form.elements.person.onchange=()=>{const p=this.people[form.elements.person.value];if(p)form.elements.usuario.value=p.usuario||[String(p.nombre||'').trim().split(' ')[0],String(p.apellido||'').trim().split(' ')[0]].filter(Boolean).join('.').toLowerCase();};
        form.onsubmit=event=>{event.preventDefault();this.create(form);};
      } else if(this.tab==='permissions') {
        panel.innerHTML=`<div class="admin-user-select"><label>Usuario existente<select data-user><option value="">Seleccione usuario</option>${this.users.map(user=>`<option value="${esc(user.usuario)}" ${user.usuario===this.target?'selected':''}>${esc(user.usuario)} · ${esc(user.rol)}${user.activo?'':' · Inactivo'}</option>`).join('')}</select></label><button data-save disabled>Guardar permisos</button></div><p data-origin class="admin-notice"></p><div data-matrix></div>`;
        panel.querySelector('[data-user]').onchange=async event=>{if(!this.canLeave()){event.target.value=this.target;return;}this.dirty=false;this.target=event.target.value;await this.permissions();};
        panel.querySelector('[data-save]').onclick=()=>this.save();
      } else {
        panel.innerHTML='<div class="admin-table" data-audit></div><div class="admin-pages"><button class="secondary" data-prev>Anterior</button><span data-page></span><button class="secondary" data-next>Siguiente</button></div>';
        panel.querySelector('[data-prev]').onclick=()=>{this.offset=Math.max(0,this.offset-100);this.audit();};
        panel.querySelector('[data-next]').onclick=()=>{this.offset+=100;this.audit();};
      }
      this.watch();
    }
    async permissions() {
      const seq=++this.sequence,target=this.target;
      const holder=this.root.querySelector('[data-matrix]');holder.innerHTML='';this.root.querySelector('[data-save]').disabled=true;
      if(!target){this.root.querySelector('[data-origin]').textContent='';return;}
      this.message('Cargando permisos...');
      try {
        const data=await this.config.request(`/admin/users/${encodeURIComponent(target)}/permissions`);
        if(this.disposed||seq!==this.sequence)return;
        const explicit=data.source==='explicit';this.baseline=explicit?data.permissions:data.inherited_permissions;
        holder.innerHTML=this.matrix(this.baseline||{});
        this.root.querySelector('[data-origin]').textContent=explicit?'Permisos explicitos guardados. Los accesos especiales heredados por usuario pueden tener prioridad.':'Permisos heredados del rol o usuario. Guardar crea una asignacion explicita; no modifica el rol base.';
        this.root.querySelector('[data-save]').disabled=false;this.watch();this.message('');
      } catch(error){if(!this.disposed&&seq===this.sequence)this.message(error.message,true);}
    }
    async create(form) {
      const person=this.people[form.elements.person.value]||{};
      const payload={usuario:form.elements.usuario.value.trim(),password:form.elements.password.value,rol:form.elements.rol.value,activo:form.elements.activo.checked,permissions:this.selectedPermissions(),source_type:person.source_type,source_id:person.source_id,nombre:person.nombre,apellido:person.apellido,email:person.email};
      if(!confirm(`Crear el usuario ${payload.usuario} con rol ${payload.rol}?`))return;
      const button=form.querySelector('[type=submit]');button.disabled=true;this.busy=true;
      try { await this.config.request('/admin/users','POST',payload);if(this.disposed)return;form.elements.password.value='';this.dirty=false;this.busy=false;await this.load();this.message(`Usuario ${payload.usuario} creado correctamente.`); }
      catch(error){this.message(error.message,true);}
      finally {payload.password='';form.elements.password.value='';button.disabled=false;this.busy=false;}
    }
    async save() {
      const permissions=this.selectedPermissions();if(!Object.keys(permissions).length){this.message('No se guardo: una matriz vacia reactivaria los permisos heredados.',true);return;}
      if(!confirm(`Guardar los permisos de ${this.target}? Esta accion modifica sus accesos.`))return;
      const button=this.root.querySelector('[data-save]');button.disabled=true;this.busy=true;
      try {await this.config.request(`/admin/users/${encodeURIComponent(this.target)}/permissions`,'PUT',{permissions});if(this.disposed)return;this.dirty=false;await this.permissions();this.message('Permisos guardados. El usuario debe volver a iniciar sesion.');}
      catch(error){this.message(error.message,true);}
      finally {button.disabled=false;this.busy=false;}
    }
    async audit() {
      const seq=++this.sequence;this.message('Cargando auditoria...');
      try {const data=await this.config.request(`/admin/users/audit?limit=100&offset=${this.offset}`);if(this.disposed||seq!==this.sequence)return;
        this.root.querySelector('[data-audit]').innerHTML=`<table><thead><tr><th>Fecha</th><th>Administrador</th><th>Usuario</th><th>Accion</th></tr></thead><tbody>${data.data.map(row=>`<tr><td>${esc(row.created_at)}</td><td>${esc(row.actor_usuario)}</td><td>${esc(row.target_usuario)}</td><td>${esc(row.action)}</td></tr>`).join('')||'<tr><td colspan="4">Sin movimientos</td></tr>'}</tbody></table>`;
        this.root.querySelector('[data-prev]').disabled=this.offset===0;this.root.querySelector('[data-next]').disabled=!data.has_more;this.root.querySelector('[data-page]').textContent=`Pagina ${this.offset/100+1}`;this.message('');
      }catch(error){if(!this.disposed&&seq===this.sequence)this.message(error.message,true);}
    }
  }
  window.SOMAdmin={mount(root,config){instance?.destroy();instance=new Admin(root,config);return instance.start();},canLeave(){return !instance||instance.canLeave();},destroy(){instance?.destroy();instance=null;}};
})();
