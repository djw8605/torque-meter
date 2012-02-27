Name:           torque-meter
Version:        1.1
Release:        1%{?dist}
Summary:        Gratia probe to collect current running stats.

Group:          Grid/Accounting
License:        Apache 2.0
URL:            http://hcc.unl.edu

# To generate source:
# git archive master --format=tar --prefix=torque-meter-1.0/ | gzip >torque-meter-1.0.tar.gz
Source0:        torque-meter-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires:       gratia-probe-common
Requires:       gratia-probe-services

BuildArch:      noarch

%description
%{summary}

%prep
%setup -q


%build


%install
rm -rf $RPM_BUILD_ROOT
install -d $RPM_BUILD_ROOT%{_sysconfdir}/gratia/torque-meter
install -m 644 ProbeConfig $RPM_BUILD_ROOT%{_sysconfdir}/gratia/torque-meter/ProbeConfig
install -m 644 meter.conf $RPM_BUILD_ROOT%{_sysconfdir}/gratia/torque-meter/meter.conf

install -d $RPM_BUILD_ROOT%{_sbindir}
install -m 700 TORQUE_meter_SAX.py $RPM_BUILD_ROOT%{_sbindir}/torque-meter

install -d $RPM_BUILD_ROOT%{_sysconfdir}/cron.d
install -m 644 torque-meter-gratia-probe.cron $RPM_BUILD_ROOT%{_sysconfdir}/cron.d/torque-meter-gratia-probe.cron

%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/gratia/torque-meter/ProbeConfig
%config(noreplace) %{_sysconfdir}/gratia/torque-meter/meter.conf
%{_sbindir}/torque-meter
%{_sysconfdir}/cron.d/torque-meter-gratia-probe.cron

%changelog
* Mon Feb 27 2012 Derek Weitzel <dweitzel@cse.unl.edu> - 1.1-1
- Updating to version 1.1 upstream

* Fri Feb 10 2012 Derek Weitzel <dweitzel@cse.unl.edu> - 1.0-6
- Fixing cron permissions

* Fri Feb 10 2012 Derek Weitzel <dweitzel@cse.unl.edu> - 1.0-5
- Fixing configuration reading

* Fri Feb 10 2012 Derek Weitzel <dweitzel@cse.unl.edu> - 1.0-4
- Cron and configuration reading

* Fri Feb 10 2012 Derek Weitzel <dweitzel@cse.unl.edu> - 1.0-3
- Fixing config files

* Fri Feb 10 2012 Derek Weitzel <dweitzel@cse.unl.edu> - 1.0-2
- Fixing Probeconfig for rpm

* Fri Feb 10 2012 Derek Weitzel <dweitzel@cse.unl.edu> - 1.0-1
- Initial package of torque-meter

