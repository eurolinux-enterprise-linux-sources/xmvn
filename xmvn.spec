Name:           xmvn
Version:        1.3.0
Release:        6%{?dist}
Summary:        Local Extensions for Apache Maven
License:        ASL 2.0
URL:            http://mizdebsk.fedorapeople.org/xmvn
BuildArch:      noarch
Source0:        https://fedorahosted.org/released/%{name}/%{name}-%{version}.tar.xz

Patch0001:      0001-Port-to-Maven-3.0.5-and-Sonatype-Aether.patch
Patch0002:      0002-Remove-integration-with-for-Apache-Ivy.patch
Patch0003:      0003-Port-to-Sonatype-Sisu.patch
Patch0004:      0004-Add-support-for-absolute-artifact-symlinks.patch
Patch0005:      0005-Ignore-runtime-exceptions-thrown-by-ASM.patch

BuildRequires:  maven >= 3.0.5-14
BuildRequires:  maven-local
BuildRequires:  beust-jcommander
BuildRequires:  cglib
BuildRequires:  maven-dependency-plugin
BuildRequires:  maven-plugin-build-helper
BuildRequires:  maven-assembly-plugin
BuildRequires:  maven-invoker-plugin
BuildRequires:  objectweb-asm
BuildRequires:  xmlunit

Requires:       maven >= 3.0.5-14

%description
This package provides extensions for Apache Maven that can be used to
manage system artifact repository and use it to resolve Maven
artifacts in offline mode, as well as Maven plugins to help with
creating RPM packages containing Maven artifacts.

%package        javadoc
Summary:        API documentation for %{name}

%description    javadoc
This package provides %{summary}.

%prep
%setup -q
%patch0001 -p1
%patch0002 -p1
%patch0003 -p1
%patch0004 -p1
%patch0005 -p1

# remove dependency plugin maven-binaries execution
# we provide apache-maven by symlink
%pom_xpath_remove "pom:executions/pom:execution[pom:id[text()='maven-binaries']]"

# get mavenVersion that is expected
mver=$(sed -n '/<mavenVersion>/{s/.*>\(.*\)<.*/\1/;p}' \
           xmvn-parent/pom.xml)
mkdir -p target/dependency/
ln -s %{_datadir}/maven target/dependency/apache-maven-$mver


# skip ITs for now (mix of old & new XMvn config causes issues
rm -rf src/it

%build
%mvn_build -X

tar --delay-directory-restore -xvf target/*tar.bz2
chmod -R +rwX %{name}-%{version}*


%install
%mvn_install

install -d -m 755 %{buildroot}%{_datadir}/%{name}
cp -r %{name}-%{version}*/* %{buildroot}%{_datadir}/%{name}/
ln -sf %{_datadir}/maven/bin/mvn %{buildroot}%{_datadir}/%{name}/bin/mvn
ln -sf %{_datadir}/maven/bin/mvnDebug %{buildroot}%{_datadir}/%{name}/bin/mvnDebug
ln -sf %{_datadir}/maven/bin/mvnyjp %{buildroot}%{_datadir}/%{name}/bin/mvnyjp


# helper scripts
install -d -m 755 %{buildroot}%{_bindir}
install -m 755 xmvn-tools/src/main/bin/tool-script \
               %{buildroot}%{_datadir}/%{name}/bin/

for tool in subst resolve bisect install;do
    rm %{buildroot}%{_datadir}/%{name}/bin/%{name}-$tool
    ln -s tool-script \
          %{buildroot}%{_datadir}/%{name}/bin/%{name}-$tool

    cat <<EOF >%{buildroot}%{_bindir}/%{name}-$tool
#!/bin/sh -e
exec %{_datadir}/%{name}/bin/%{name}-$tool "\${@}"
EOF
    chmod +x %{buildroot}%{_bindir}/%{name}-$tool

done

# copy over maven lib directory
cp -r %{_datadir}/maven/lib/* %{buildroot}%{_datadir}/%{name}/lib/

# possibly recreate symlinks that can be automated with xmvn-subst
%{name}-subst %{buildroot}%{_datadir}/%{name}/

# XXX temp until guice is rebuilt and no_aop has proper manifest so that xmvn-subst will work on it
for tool in subst resolver bisect installer;do
    # guice-no_aop doesn't contain correct pom.properties. Manually replace with symlinks
    pushd %{buildroot}%{_datadir}/%{name}/lib/$tool
       rm -f %{buildroot}%{_datadir}/%{name}/lib/google-guice*
       rm -f %{buildroot}%{_datadir}/%{name}/lib/sisu-guice*
       build-jar-repository . guice/google-guice-no_aop
    popd
done
rm -f %{buildroot}%{_datadir}/%{name}/lib/google-guice*
rm -f %{buildroot}%{_datadir}/%{name}/lib/sisu-guice*
build-jar-repository %{buildroot}%{_datadir}/%{name}/lib/ guice/google-guice-no_aop

# reenable after build
#if [[ `find %{buildroot}%{_datadir}/%{name}/lib -type f -name '*.jar' -not -name '*%{name}*' | wc -l` -ne 0 ]];then
#    echo "Some jar files were not symlinked during build. Aborting"
#    exit 1
#fi


# /usr/bin/xmvn script
cat <<EOF >%{buildroot}%{_bindir}/%{name}
#!/bin/sh -e
export M2_HOME="\${M2_HOME:-%{_datadir}/%{name}}"
exec mvn "\${@}"
EOF

# make sure our conf is identical to maven so yum won't freak out
cp -P %{_datadir}/maven/conf/settings.xml %{buildroot}%{_datadir}/%{name}/conf/

%pretrans -p <lua>
-- we changed symlink to dir in 0.5.0-1, workaround RPM issues
for key, dir in pairs({"conf", "conf/logging", "boot"}) do
    path = "%{_datadir}/%{name}/" .. dir
    if posix.readlink(path) then
       os.remove(path)
    end
end

%files -f .mfiles
%doc LICENSE NOTICE
%doc AUTHORS README
%attr(755,-,-) %{_bindir}/*
%{_datadir}/%{name}

%files javadoc -f .mfiles-javadoc
%doc LICENSE NOTICE

%changelog
* Wed Oct  5 2016 Mikolaj Izdebski <mizdebsk@redhat.com> - 1.3.0-6
- Ignore runtime exceptions thrown by ASM
- Resolves: rhbz#1381883

* Fri Jan 10 2014 Mikolaj Izdebski <mizdebsk@redhat.com> - 1.3.0-5
- Split 1 patch to 3 patches, one per feature
- Add support for absolute artifact symlinks

* Fri Dec 27 2013 Daniel Mach <dmach@redhat.com> - 1.3.0-4
- Mass rebuild 2013-12-27

* Thu Nov  7 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 1.3.0-3
- Fix guice symlinks

* Thu Nov  7 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 1.3.0-2
- Bump Maven requirement to 3.0.5-14

* Thu Nov  7 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 1.3.0-1
- Rebase upstream version 1.3.0

* Tue Oct 01 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> - 1.1.0-1
- Update to upstream version 1.1.0

* Fri Sep 27 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> - 1.0.2-3
- Add __default package specifier support

* Mon Sep 23 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 1.0.2-2
- Don't try to relativize symlink targets
- Restotre support for relative symlinks

* Fri Sep 20 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 1.0.2-1
- Update to upstream version 1.0.2

* Tue Sep 10 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> - 1.0.0-2
- Workaround broken symlinks for core and connector (#986909)

* Mon Sep 09 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> - 1.0.0-1
- Updating to upstream 1.0.0

* Tue Sep  3 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> 1.0.0-0.2.alpha1
- Update to upstream version 1.0.0 alpha1

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.5.1-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Tue Jul 23 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.5.1-3
- Rebuild without bootstrapping

* Tue Jul 23 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.5.1-2
- Install symlink to simplelogger.properties in %{_sysconfdir}

* Tue Jul 23 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.5.1-1
- Update to upstream version 0.5.1

* Tue Jul 23 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.5.0-7
- Allow installation of Eclipse plugins in javadir

* Mon Jul 22 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.5.0-6
- Remove workaround for plexus-archiver bug
- Use sonatype-aether symlinks

* Fri Jun 28 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.5.0-5
- Rebuild to regenerate API documentation
- Resolves: CVE-2013-1571

* Wed Jun  5 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.5.0-5
- Fix resolution of tools.jar

* Fri May 31 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.5.0-4
- Fix handling of packages with dots in groupId
- Previous versions also fixed bug #948731

* Tue May 28 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.5.0-3
- Move pre scriptlet to pretrans and implement in lua

* Fri May 24 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.5.0-2
- Fix upgrade path scriptlet
- Add patch to fix NPE when debugging is disabled

* Fri May 24 2013 Stanislav Ochotnicky <sochotnicky@redhat.com> - 0.5.0-1
- Update to upstream version 0.5.0

* Fri May 17 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.4.2-3
- Add patch: install MOJO fix

* Wed Apr 17 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.4.2-2
- Update plexus-containers-container-default JAR location

* Tue Apr  9 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.4.2-1
- Update to upstream version 0.4.2

* Thu Mar 21 2013 Michal Srb <msrb@redhat.com> - 0.4.1-1
- Update to upstream version 0.4.1

* Fri Mar 15 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.4.0-1
- Update to upstream version 0.4.0

* Fri Mar 15 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.4.0-0.7
- Enable tests

* Thu Mar 14 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.4.0-0.6
- Update to newer snapshot

* Wed Mar 13 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.4.0-0.5
- Update to newer snapshot

* Wed Mar 13 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.4.0-0.4
- Set proper permissions for scripts in _bindir

* Tue Mar 12 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.4.0-0.3
- Update to new upstream snapshot
- Create custom /usr/bin/xmvn instead of using %%jpackage_script
- Mirror maven directory structure
- Add Plexus Classworlds config file

* Wed Mar  6 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.4.0-0.2
- Update to newer snapshot

* Wed Mar  6 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.4.0-0.1
- Update to upstream snapshot of version 0.4.0

* Mon Feb 25 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.3.1-2
- Install effective POMs into a separate directory

* Thu Feb  7 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.3.1-1
- Update to upstream version 0.3.1

* Tue Feb  5 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.3.0-1
- Update to upstream version 0.3.0
- Don't rely on JPP symlinks when resolving artifacts
- Blacklist more artifacts
- Fix dependencies

* Thu Jan 24 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.2.6-1
- Update to upstream version 0.2.6

* Mon Jan 21 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.2.5-1
- Update to upstream version 0.2.5

* Fri Jan 11 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.2.4-1
- Update to upstream version 0.2.4

* Wed Jan  9 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.2.3-1
- Update to upstream version 0.2.3

* Tue Jan  8 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.2.2-1
- Update to upstream version 0.2.2

* Tue Jan  8 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.2.1-1
- Update to upstream version 0.2.1

* Mon Jan  7 2013 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.2.0-1
- Update to upstream version 0.2.0
- New major features: depmaps, compat symlinks, builddep MOJO
- Install effective POMs for non-POM artifacts
- Multiple major and minor bugfixes
- Drop support for resolving artifacts from %%_javajnidir

* Fri Dec  7 2012 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.1.5-1
- Update to upstream version 0.1.5

* Fri Dec  7 2012 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.1.4-1
- Update to upstream version 0.1.4

* Fri Dec  7 2012 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.1.3-1
- Update to upstream version 0.1.3

* Fri Dec  7 2012 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.1.2-1
- Update to upstream version 0.1.2

* Fri Dec  7 2012 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.1.1-1
- Update to upstream version 0.1.1

* Thu Dec  6 2012 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.1.0-1
- Update to upstream version 0.1.0
- Implement auto requires generator

* Mon Dec  3 2012 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.0.2-1
- Update to upstream version 0.0.2

* Thu Nov 29 2012 Mikolaj Izdebski <mizdebsk@redhat.com> - 0.0.1-1
- Update to upstream version 0.0.1

* Wed Nov 28 2012 Mikolaj Izdebski <mizdebsk@redhat.com> - 0-2
- Add jpackage scripts

* Mon Nov  5 2012 Mikolaj Izdebski <mizdebsk@redhat.com> - 0-1
- Initial packaging
