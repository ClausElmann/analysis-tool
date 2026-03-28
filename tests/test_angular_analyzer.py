"""Tests for AngularAnalyzer."""

import pytest

from analyzers.angular_analyzer import AngularAnalyzer
from core.model import FileAnalysis


def make_analysis(path="app.component.ts"):
    return FileAnalysis(project="test", path=path, type="angular", technology="angular")


def make_analyzer():
    return AngularAnalyzer()


# 1. Valid Angular component file
def test_angular_valid_component():
    content = """
import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-order-list',
  templateUrl: './order-list.component.html'
})
export class OrderListComponent implements OnInit {
  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.http.get('/api/orders').subscribe();
    this.http.post('/api/orders', {}).subscribe();
  }
}
"""
    analyzer = make_analyzer()
    analysis = make_analysis("order-list.component.ts")
    analyzer.analyze("order-list.component.ts", content, analysis)

    assert analysis.summary != ""
    assert "classes" in analysis.key_elements
    assert isinstance(analysis.key_elements["classes"], list)
    assert "OrderListComponent" in analysis.key_elements["classes"]
    assert "selectors" in analysis.key_elements
    assert isinstance(analysis.key_elements["selectors"], list)
    assert "app-order-list" in analysis.key_elements["selectors"]
    assert isinstance(analysis.domain_signals.get("roles", []), list)
    assert "component" in analysis.domain_signals["roles"]


# 2. Partial / minimal Angular file (service with HTTP but missing decorator)
def test_angular_partial_service():
    content = """
export class DataService {
  fetchData() {
    return this.http.get('/api/data');
  }
  saveData(payload) {
    return this.http.post('/api/data', payload);
  }
}
"""
    analyzer = make_analyzer()
    analysis = make_analysis("data.service.ts")
    analyzer.analyze("data.service.ts", content, analysis)

    assert "classes" in analysis.key_elements
    assert isinstance(analysis.key_elements["classes"], list)
    assert "DataService" in analysis.key_elements["classes"]
    assert "http_calls" in analysis.key_elements
    assert isinstance(analysis.key_elements["http_calls"], list)
    assert len(analysis.key_elements["http_calls"]) >= 2
    assert isinstance(analysis.inputs_outputs.get("api_operations", []), list)


# 3. Empty / no signals
def test_angular_empty_content():
    content = ""
    analyzer = make_analyzer()
    analysis = make_analysis("empty.ts")
    analyzer.analyze("empty.ts", content, analysis)

    assert analysis.summary != ""
    assert isinstance(analysis.key_elements.get("classes", []), list)
    assert isinstance(analysis.key_elements.get("selectors", []), list)
    assert isinstance(analysis.key_elements.get("routes", []), list)
    assert isinstance(analysis.domain_signals.get("roles", []), list)
    assert isinstance(analysis.risks_notes, list)
    assert analysis.raw_extract is not None


# 4. Edge case: routing module with multiple routes
def test_angular_routing_module():
    content = """
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { OrderListComponent } from './order-list/order-list.component';
import { DashboardComponent } from './dashboard/dashboard.component';

const routes: Routes = [
  { path: 'orders', component: OrderListComponent },
  { path: 'dashboard', component: DashboardComponent },
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
"""
    analyzer = make_analyzer()
    analysis = make_analysis("app.routing.module.ts")
    analyzer.analyze("app.routing.module.ts", content, analysis)

    assert "routes" in analysis.key_elements
    assert isinstance(analysis.key_elements["routes"], list)
    assert len(analysis.key_elements["routes"]) > 0
    assert "classes" in analysis.key_elements
    assert "AppRoutingModule" in analysis.key_elements["classes"]
    assert isinstance(analysis.domain_signals.get("roles", []), list)
    assert isinstance(analysis.dependencies.get("ui_assets", []), list)
